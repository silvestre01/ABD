# =============================
# Smörgås Kaffet - Aplicación Flask (MariaDB)
# Programa principal: rutas, conexión MariaDB (PyMySQL), autenticación,
# CRUD de compras y edición inline de detalle. (+ Bloqueo pesimista)
# =============================

import secrets
import re
import json
import os
from datetime import date, datetime, timedelta
from functools import wraps
from decimal import Decimal

import pymysql
from pymysql.cursors import DictCursor
from pymysql.err import IntegrityError, OperationalError
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from waitress import serve

# ---------------- Configuración Flask ----------------
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY", "clave_super_secreta")

# ---------------- Configuración de sesión Flask ----------------
# Tiempo máximo de inactividad (minutos)
app.config["SESSION_TTL_MIN"] = 30  # 30 min, puedes ajustar
SESSION_TTL_MIN = app.config["SESSION_TTL_MIN"]


# ---------------- Configuración BD (MariaDB) ----------------
# Config común sin el usuario/contraseña (se eligen según la sesión)
BASE_DB_CFG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "shirley",
    "database": "smorgas_kaffet",
    "cursorclass": pymysql.cursors.DictCursor
}

# Credenciales por rol para abrir la BD
ROLE_DB_CREDENTIALS = {
    "admin":  {"user": "admin",  "password": "admin"},
    "mesero": {"user": "mesero", "password": "mesero"},
}

# Credenciales por defecto (cuando no hay sesión: ej. /register, /login GET)
DEFAULT_DB_USER = os.getenv("DB_USER_DEFAULT", "root")
DEFAULT_DB_PASS = os.getenv("DB_PASS_DEFAULT", "shirley")

def get_db_connection():
    """
    Abre una conexión a MariaDB con credenciales dinámicas:
    - Si hay sesión y rol: usa las credenciales mapeadas (admin/mesero).
    - Si no hay sesión/rol: usa credenciales por defecto (root o variables de entorno).
    - Fija nivel de aislamiento por sesión: READ COMMITTED (reduce bloqueos largos/lecturas repetidas).
    """
    cfg = dict(BASE_DB_CFG)
    rol = session.get("rol")
    creds = ROLE_DB_CREDENTIALS.get(rol)

    if creds:
        cfg.update(user=creds["user"], password=creds["password"])
    else:
        cfg.update(user=DEFAULT_DB_USER, password=DEFAULT_DB_PASS)

    conn = pymysql.connect(**cfg)
    # Aislamiento pesimista razonable para concurrencia de edición
    with conn.cursor() as cur:
        cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    return conn

# ---------- Helper de retry ante deadlocks / timeouts ----------
def tx_with_retry(fn, retries=3):
    """
    Ejecuta una función transaccional 'fn()' con reintentos
    si ocurre deadlock (1213) o lock wait timeout (1205).
    La función 'fn' debe encargarse de abrir/cerrar su conexión y commit/rollback.
    """
    for i in range(retries):
        try:
            return fn()
        except OperationalError as e:
            code = e.args[0] if e.args else None
            if code in (1213, 1205) and i < retries - 1:
                # reintenta
                continue
            raise

# ---------------- Helpers ----------------
def _now_sql():
    # Usa hora del servidor DB; si prefieres UTC en app, puedes usar datetime.utcnow()
    return datetime.now()

def _session_active(cur, row_now):
    """
    Determina si una sesión queda activa:
    - Session_Expira > ahora
    - Ultimo_Visto dentro de la ventana
    """
    if not row_now or not row_now.get("Session_Expira"):
        return False
    ahora = _now_sql()
    expira = row_now["Session_Expira"]
    uv = row_now.get("Ultimo_Visto")
    if expira and expira > ahora:
        if not uv:
            return True
        # si último visto está dentro del TTL, se considera activa
        return (ahora - uv) <= timedelta(minutes=SESSION_TTL_MIN)
    return False

def _bump_session(cur, id_usuario):
    """Desliza la ventana de sesión (heartbeat)."""
    nueva_exp = _now_sql() + timedelta(minutes=SESSION_TTL_MIN)
    cur.execute("""
        UPDATE TBL_USUARIOS
           SET Ultimo_Visto = NOW(),
               Session_Expira = %s
         WHERE ID_Usuario = %s
    """, (nueva_exp, id_usuario))


def as_float(value):
    """Convierte Decimal/None a float de forma segura para JSON/render."""
    if value is None:
        return 0.0
    return float(value) if isinstance(value, (Decimal, int, float)) else value

def login_requerido(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "usuario" not in session or "sess_token" not in session:
            return redirect(url_for("login"))

        user  = session.get("usuario")
        token = session.get("sess_token")

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ID_Usuario, Session_Token, Session_Expira, Ultimo_Visto
                      FROM TBL_USUARIOS
                     WHERE Nombre_Usuario=%s
                """, (user,))
                row = cur.fetchone()

                # 1) Si no hay fila/token en BD o no coincide -> invalidar cookie
                if not row or not row.get("Session_Token") or row["Session_Token"] != token:
                    session.clear()
                    flash("Tu sesión ya no es válida (iniciada en otro dispositivo o cerrada).", "warning")
                    return redirect(url_for("login"))

                # 2) Si caducó la sesión -> invalidar
                if not _session_active(cur, row):
                    # limpiar en BD por consistencia
                    cur.execute("""
                        UPDATE TBL_USUARIOS
                           SET Session_Token = NULL,
                               Session_Expira = NULL
                         WHERE ID_Usuario   = %s
                    """, (row["ID_Usuario"],))
                    conn.commit()
                    session.clear()
                    flash("Tu sesión ha expirado por inactividad.", "warning")
                    return redirect(url_for("login"))

                # 3) Heartbeat (extender vigencia deslizante)
                _bump_session(cur, row["ID_Usuario"])
            conn.commit()
        finally:
            conn.close()

        return f(*args, **kwargs)
    return wrapped


def parse_fecha_ui(fecha_str: str) -> datetime:
    """Devuelve un datetime a partir de 'YYYY-MM-DD' o 'DD/MM/YYYY'."""
    fecha_str = (fecha_str or "").strip()
    if not fecha_str:
        raise ValueError("Fecha vacía")
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d")
    except ValueError:
        return datetime.strptime(fecha_str, "%d/%m/%Y")

def admin_requerido(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        if session.get("rol") != "admin":
            flash("Solo administradores.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapped

# ---------------- Home ----------------
@app.route("/")
@login_requerido
def index():
    """
    Página principal: lista las compras (TBL_COMPRA), mostrando:
      - Folio, Mesa, Importe_Total, Cantidad_Total, ID_Modo_Entrega
    LEFT JOIN con TBL_MODO_ENTREGA (si existe):
      - Si no hay coincidencia, muestra texto por defecto con CASE.
    Renderiza templates/index.html.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.Folio,
                    c.ID_Mesa,
                    c.Importe_Total,
                    c.Cantidad_Total,
                    c.ID_Modo_Entrega,
                    COALESCE(
                        m.Modo_Entrega,
                        CASE c.ID_Modo_Entrega
                            WHEN 1 THEN 'Llevar'
                            WHEN 2 THEN 'Comedor'
                            ELSE '—'
                        END
                    ) AS Modo_Entrega
                FROM TBL_COMPRA AS c
                LEFT JOIN TBL_MODO_ENTREGA AS m
                       ON m.ID_Modo_Entrega = c.ID_Modo_Entrega
                ORDER BY c.Folio DESC
                """
            )
            ventas = cur.fetchall()
            for v in ventas:
                v["Importe_Total"] = as_float(v.get("Importe_Total"))
    finally:
        conn.close()

    return render_template(
        "index.html",
        ventas=ventas,
        usuario=session.get("usuario"),
        rol=session.get("rol"),
    )

# ---------- Detalle (para editor inline del index) ----------
@app.route("/venta/<int:folio>/detalles")
@login_requerido
def venta_detalles(folio):
    """
    Devuelve en JSON el detalle (renglones) de un folio:
      - ID_Detalle, Folio, ID_Producto, Cantidad, Precio_Unit, Subtotal, Nombre_Producto
    (Solo lectura: sin bloqueos explícitos)
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.ID_Detalle, d.Folio, d.ID_Producto, d.Cantidad, d.Precio_Unit, d.Subtotal,
                       p.Nombre_Producto
                  FROM TBL_DETALLE d
                  JOIN TBL_PRODUCTO p ON p.ID_Producto = d.ID_Producto
                 WHERE d.Folio = %s
                 ORDER BY d.ID_Detalle
                """,
                (folio,),
            )
            rows = cur.fetchall()
            for r in rows:
                r["Precio_Unit"] = as_float(r.get("Precio_Unit"))
                r["Subtotal"] = as_float(r.get("Subtotal"))
    finally:
        conn.close()

    return jsonify(rows)

@app.route("/detalle/update/<int:id_detalle>", methods=["POST"])
@login_requerido
def detalle_update(id_detalle):
    """
    Actualiza un renglón de detalle con BLOQUEO PESIMISTA:
      - Valida cantidad (1–50) y precio (0.01–10000)
      - Bloquea el folio afectado (cabecera y todos los detalles) con SELECT ... FOR UPDATE
      - Actualiza renglón, recalcula totales y actualiza cabecera
      - Reintenta si hay deadlock / lock wait timeout
    """
    try:
        cant = int(request.form.get("cantidad", ""))
        precio = float(request.form.get("precio_unit", ""))
    except ValueError:
        return jsonify({"ok": False, "msg": "Datos inválidos"}), 400

    if not (1 <= cant <= 50) or not (0.01 <= precio <= 10000):
        return jsonify({"ok": False, "msg": "Fuera de rango"}), 400

    def _tx():
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 1) Identifica y BLOQUEA el folio por orden estable
                cur.execute("SELECT Folio FROM TBL_DETALLE WHERE ID_Detalle=%s FOR UPDATE", (id_detalle,))
                r = cur.fetchone()
                if not r:
                    conn.rollback()
                    return jsonify({"ok": False, "msg": "Detalle inexistente"}), 404
                folio = r["Folio"]

                # 2) Bloquea cabecera y luego todos los detalles del folio (orden estable para evitar deadlocks)
                cur.execute("SELECT Folio FROM TBL_COMPRA WHERE Folio=%s FOR UPDATE", (folio,))
                cur.execute("SELECT ID_Detalle FROM TBL_DETALLE WHERE Folio=%s FOR UPDATE", (folio,))

                # 3) Actualiza el renglón
                subtotal = cant * precio
                cur.execute(
                    """
                    UPDATE TBL_DETALLE
                       SET Cantidad = %s, Precio_Unit = %s, Subtotal = %s
                     WHERE ID_Detalle = %s
                    """,
                    (cant, precio, subtotal, id_detalle),
                )

                # 4) Recalcula totales y actualiza cabecera
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(Cantidad),0) AS Cantidad_Total,
                        COALESCE(SUM(Subtotal),0) AS Importe_Total
                      FROM TBL_DETALLE
                     WHERE Folio=%s
                    """,
                    (folio,),
                )
                tot = cur.fetchone() or {"Cantidad_Total": 0, "Importe_Total": 0}
                cur.execute(
                    """
                    UPDATE TBL_COMPRA
                       SET Cantidad_Total = %s, Importe_Total = %s
                     WHERE Folio = %s
                    """,
                    (tot["Cantidad_Total"], tot["Importe_Total"], folio),
                )

            conn.commit()
            return jsonify({"ok": True})
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    try:
        return tx_with_retry(_tx)
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error al actualizar: {e}"}), 500

# ---------- Editar cabecera ----------
@app.route("/update/<int:folio>", methods=["POST"])
@login_requerido
def update(folio):
    """
    Edita la cabecera de una compra (ID_Mesa, ID_Modo_Entrega) con BLOQUEO PESIMISTA:
      - Bloquea cabecera y todos los detalles del folio con SELECT ... FOR UPDATE
      - Actualiza cabecera
      - Reintenta si hay deadlock / timeout
    """
    id_mesa = request.form.get("ID_Mesa")
    id_modo = request.form.get("ID_Modo_Entrega")

    if id_mesa not in [str(x) for x in range(100, 109)]:
        flash("Mesa inválida.", "warning")
        return redirect(url_for("index"))
    if id_modo not in ("1", "2"):
        flash("Modo de entrega inválido.", "warning")
        return redirect(url_for("index"))

    def _tx():
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Bloquea cabecera y detalles (orden estable)
                cur.execute("SELECT Folio FROM TBL_COMPRA WHERE Folio=%s FOR UPDATE", (folio,))
                cur.execute("SELECT ID_Detalle FROM TBL_DETALLE WHERE Folio=%s FOR UPDATE", (folio,))
                # Actualiza cabecera
                cur.execute(
                    "UPDATE TBL_COMPRA SET ID_Mesa=%s, ID_Modo_Entrega=%s WHERE Folio=%s",
                    (id_mesa, id_modo, folio),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    try:
        tx_with_retry(_tx)
        flash(f"Cuenta #{folio} actualizada.", "success")
    except Exception as e:
        flash(f"Error al actualizar: {e}", "danger")

    return redirect(url_for("index"))

# ---------- Eliminar cuenta (solo admin) ----------
@app.route("/delete/<int:folio>")
@login_requerido
def delete(folio):
    """
    Elimina definitivamente una cuenta con BLOQUEO PESIMISTA:
      - Solo administradores.
      - Bloquea cabecera y detalles del folio con SELECT ... FOR UPDATE
      - Elimina detalle y luego cabecera
      - Reintenta si hay deadlock / timeout
    """
    if session.get("rol") != "admin":
        flash("Solo administradores pueden eliminar.", "danger")
        return redirect(url_for("index"))

    def _tx():
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Bloquear en orden: cabecera -> detalles
                cur.execute("SELECT Folio FROM TBL_COMPRA WHERE Folio=%s FOR UPDATE", (folio,))
                cur.execute("SELECT ID_Detalle FROM TBL_DETALLE WHERE Folio=%s FOR UPDATE", (folio,))

                # Eliminar primero detalles, luego cabecera
                cur.execute("DELETE FROM TBL_DETALLE WHERE Folio = %s", (folio,))
                cur.execute("DELETE FROM TBL_COMPRA  WHERE Folio = %s", (folio,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    try:
        tx_with_retry(_tx)
        flash(f"Folio #{folio} eliminado.", "success")
    except Exception as e:
        flash(f"Error al eliminar: {e}", "danger")

    return redirect(url_for("index"))

# ---------------- Nueva cuenta (form) ----------------
@app.route("/pagina2")
@login_requerido
def pagina2():
    """
    Muestra el formulario para crear una cuenta:
      - Carga catálogo de productos por categoría
      - Pasa 'hoy' como fecha (usa min=max en el input del template para solo hoy).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ID_Producto, Nombre_Producto, Precio_Producto,
                       COALESCE(Categoria,'Otros') AS Categoria
                  FROM TBL_PRODUCTO
                 ORDER BY Categoria, Nombre_Producto
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    catalogo = {}
    for r in rows:
        catalogo.setdefault(r["Categoria"], []).append({
            "id": r["ID_Producto"],
            "nombre": r["Nombre_Producto"],
            "precio": as_float(r["Precio_Producto"]),
        })

    hoy = date.today().isoformat()
    return render_template(
        "pagina2.html",
        catalogo=catalogo,
        hoy=hoy,  # En el template: <input type="date" min="{{hoy}}" max="{{hoy}}" ...>
        usuario=session.get("usuario"),
        rol=session.get("rol"),
    )

# ---------------- Guardar nueva cuenta ----------------
@app.route("/add", methods=["POST"])
@login_requerido
def add():
    id_mesa = request.form.get("id_mesa")
    id_modo_entrega = request.form.get("id_modo_entrega")
    detalles_json = request.form.get("detalles")

    if not id_mesa or not detalles_json:
        flash("Datos incompletos para registrar la cuenta.", "warning")
        return redirect(url_for("pagina2"))

    try:
        detalles = json.loads(detalles_json)
    except json.JSONDecodeError:
        flash("Error en los detalles del pedido.", "danger")
        return redirect(url_for("pagina2"))

    if not detalles:
        flash("Agrega al menos un producto.", "warning")
        return redirect(url_for("pagina2"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # ---- Fecha/Hora normalizada (fecha en TBL_FECHA, hora en COMPRA)
            now = datetime.now()
            dia, mes, anio = now.day, now.month, now.year
            hora_str = now.strftime("%H:%M:%S")

            cur.execute("""
                SELECT ID_Fecha FROM TBL_FECHA
                WHERE Dia=%s AND Mes=%s AND Anio=%s
            """, (dia, mes, anio))
            row = cur.fetchone()
            if row: id_fecha = row["ID_Fecha"]
            else:
                cur.execute("INSERT INTO TBL_FECHA (Dia, Mes, Anio) VALUES (%s,%s,%s)", (dia, mes, anio))
                id_fecha = cur.lastrowid

            # ---- Totales
            suma_cantidades = sum(int(d["cantidad"]) for d in detalles)
            total_importe   = sum(float(d["precio"]) * int(d["cantidad"]) for d in detalles)

            cur.execute("""
                 INSERT INTO TBL_COMPRA (ID_Fecha, ID_Mesa, Hora, Cantidad_Total, Importe_Total, ID_Modo_Entrega)
                 VALUES (%s, %s, %s, %s, %s, %s)""", (id_fecha, id_mesa, hora_str, suma_cantidades, total_importe, id_modo_entrega))
            # ==========================================================

            folio = cur.lastrowid

            # ---- Detalle
            for d in detalles:
                cur.execute("""
                    INSERT INTO TBL_DETALLE (Folio, ID_Producto, Cantidad, Precio_Unit)
                    VALUES (%s, %s, %s, %s)
                """, (folio, d["id_producto"], d["cantidad"], d["precio"]))

        conn.commit()
        flash("Cuenta registrada correctamente.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al registrar la cuenta: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("index"))

# ---------------- Registro / Login / Logout ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Registro de usuarios usando el mismo login.html (register_mode=True).
    Evita duplicados a nivel BD + captura atómica del INSERT.
    """
    if request.method == "GET":
        return render_template("login.html", register_mode=True)

    # Campos que envía tu HTML
    nombre = (request.form.get("usuario") or "").strip()
    pw     = (request.form.get("contrasenia") or "").strip()
    rol    = (request.form.get("rol") or "mesero").strip()

    # --- Validaciones servidor (coherentes con tu formulario) ---
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{1,10}", nombre):
        flash("El usuario debe contener solo letras y máximo 10 caracteres.", "warning")
        return render_template("login.html", register_mode=True)

    if not (1 <= len(pw) <= 10):
        flash("La contraseña debe tener de 1 a 10 caracteres.", "warning")
        return render_template("login.html", register_mode=True)

    if rol not in ("admin", "mesero"):
        rol = "mesero"

    pw_hash = generate_password_hash(pw)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # INSERT directo (sin SELECT previo) para evitar TOCTTOU
            cur.execute("""
                INSERT INTO TBL_USUARIOS
                    (Nombre_Usuario, Rol_Usuario, Contrasenia_hash, Fecha_Creacion)
                VALUES (%s, %s, %s, NOW())
            """, (nombre, rol, pw_hash))
        conn.commit()
        flash(f"Usuario «{nombre}» registrado correctamente.", "success")
        return redirect(url_for("login"))

    except IntegrityError as e:
        conn.rollback()
        # 1062 => Duplicate entry for key (índice UNIQUE lo disparó)
        if getattr(e, "args", None) and e.args[0] == 1062:
            flash("Ese nombre de usuario ya está registrado.", "danger")
            return render_template("login.html", register_mode=True)
        # Otros errores de BD
        flash(f"Error al registrar: {e}", "danger")
        return render_template("login.html", register_mode=True)

    finally:
        conn.close()

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Inicia sesión con validación de usuario/contraseña,
    control de sesión única por usuario (no permite doble acceso simultáneo).
    """
    if request.method == "GET":
        return render_template("login.html", register_mode=False)

    # --- Obtener datos del formulario ---
    usuario = (request.form.get("usuario") or "").strip()
    password = (request.form.get("contrasenia") or "").strip()

    # Validación básica del lado servidor
    if not usuario or not password:
        flash("Debes ingresar usuario y contraseña.", "warning")
        return render_template("login.html", register_mode=False)

    # Conexión a la BD
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ID_Usuario, Nombre_Usuario, Rol_Usuario, Contrasenia_hash,
                       Session_Token, Session_Expira, Ultimo_Visto
                  FROM TBL_USUARIOS
                 WHERE Nombre_Usuario = %s
            """, (usuario,))
            row = cur.fetchone()

            # Usuario no encontrado
            if not row:
                flash("Usuario no encontrado.", "danger")
                return render_template("login.html", register_mode=False)

            # Verificar contraseña
            if not check_password_hash(row["Contrasenia_hash"], password):
                flash("Contraseña incorrecta.", "danger")
                return render_template("login.html", register_mode=False)

            # --------------------------
            # Validar sesión activa (bloqueo simultáneo)
            # --------------------------
            ahora = datetime.now()
            expira = row.get("Session_Expira")
            if row.get("Session_Token") and expira and expira > ahora:
                flash("Esta cuenta ya está activa en otro dispositivo.", "danger")
                return render_template("login.html", register_mode=False)

            # --------------------------
            # Crear nueva sesión única
            # --------------------------
            token = secrets.token_hex(16)
            nueva_exp = ahora + timedelta(minutes=SESSION_TTL_MIN)
            cur.execute("""
                UPDATE TBL_USUARIOS
                   SET Session_Token = %s,
                       Session_Expira = %s,
                       Ultimo_Visto   = NOW()
                 WHERE ID_Usuario = %s
            """, (token, nueva_exp, row["ID_Usuario"]))
        conn.commit()

    except OperationalError as e:
        flash(f"Error de conexión a la BD: {e}", "danger")
        return render_template("login.html", register_mode=False)

    finally:
        conn.close()

    # --------------------------
    # Crear sesión Flask
    # --------------------------
    session.clear()
    session["usuario"] = row["Nombre_Usuario"]
    session["rol"] = row["Rol_Usuario"]
    session["sess_token"] = token
    session.permanent = True  # activa expiración automática
    app.permanent_session_lifetime = timedelta(minutes=SESSION_TTL_MIN)

    flash(f"Bienvenido, {row['Nombre_Usuario']}!", "success")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    user = session.get("usuario")
    token = session.get("sess_token")

    if user and token:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT ID_Usuario, Session_Token FROM TBL_USUARIOS WHERE Nombre_Usuario=%s", (user,))
                row = cur.fetchone()
                if row and row.get("Session_Token") == token:
                    cur.execute("""
                        UPDATE TBL_USUARIOS
                           SET Session_Token = NULL,
                               Session_Expira = NULL,
                               Ultimo_Visto   = NOW()
                         WHERE ID_Usuario   = %s
                    """, (row["ID_Usuario"],))
            conn.commit()
        finally:
            conn.close()

    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("login"))


# ---------------- Administración de usuarios (solo admin) ----------------
@app.route("/usuarios")
@admin_requerido
def usuarios_list():
    """
    Lista usuarios desde TBL_USUARIOS para permitir su eliminación por el admin.
    NOTA: las contraseñas se almacenan como hash (no descifrables).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ID_Usuario, Nombre_Usuario, Rol_Usuario, Contrasenia_hash, Fecha_Creacion
                  FROM TBL_USUARIOS
                 ORDER BY ID_Usuario
            """)
            usuarios = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "ElimUs.html",
        usuarios=usuarios,
        usuario=session.get("usuario"),
        rol=session.get("rol"),
    )

@app.route("/usuarios/reset/<int:id_usuario>", methods=["POST"])
@admin_requerido
def usuario_reset_password(id_usuario):
    """
    Restablece la contraseña de un usuario (solo admin).
    Valida longitud (1..10, como tu login) y coincidencia.
    """
    new_pw = (request.form.get("new_password") or "").strip()
    new_pw2 = (request.form.get("confirm_password") or "").strip()

    if not new_pw or len(new_pw) > 10:
        flash("La nueva contraseña debe tener de 1 a 10 caracteres.", "warning")
        return redirect(url_for("usuarios_list"))
    if new_pw != new_pw2:
        flash("Las contraseñas no coinciden.", "warning")
        return redirect(url_for("usuarios_list"))

    pw_hash = generate_password_hash(new_pw)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Nombre_Usuario FROM TBL_USUARIOS WHERE ID_Usuario=%s", (id_usuario,))
            row = cur.fetchone()
            if not row:
                flash("Usuario no encontrado.", "warning")
                return redirect(url_for("usuarios_list"))

            cur.execute(
                "UPDATE TBL_USUARIOS SET Contrasenia_hash=%s WHERE ID_Usuario=%s",
                (pw_hash, id_usuario),
            )
        conn.commit()
        flash(f"Contraseña restablecida para «{row['Nombre_Usuario']}».", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al restablecer: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("usuarios_list"))

@app.route("/usuarios/delete/<int:id_usuario>", methods=["POST"])
@admin_requerido
def usuario_delete(id_usuario):
    """
    Elimina un usuario por ID_Usuario. Protegido a admin.
    Evita borrar al propio admin logueado para no dejar el sistema sin usuarios.
    """
    # Evitar que el admin actual se borre a sí mismo
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Nombre_Usuario, Rol_Usuario FROM TBL_USUARIOS WHERE ID_Usuario=%s", (id_usuario,))
            row = cur.fetchone()
            if not row:
                flash("Usuario no encontrado.", "warning")
                return redirect(url_for("usuarios_list"))

            if row["Nombre_Usuario"] == session.get("usuario"):
                flash("No puedes eliminar tu propio usuario en esta vista.", "warning")
                return redirect(url_for("usuarios_list"))

            # Si hay tablas que referencian usuarios, deberías manejar FK/ON DELETE RESTRICT/SET NULL.
            cur.execute("DELETE FROM TBL_USUARIOS WHERE ID_Usuario=%s", (id_usuario,))
        conn.commit()
        flash(f"Usuario «{row['Nombre_Usuario']}» eliminado.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error al eliminar: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("usuarios_list"))


# ---------------- Run ----------------
if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000, threads=8) #La IP es del internet de MAUI
    #app.run(host="192.168.0.87", port=5000, debug=True, threaded=True)  # Para desarrollo en casa

