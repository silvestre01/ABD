-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Versión del servidor:         12.2.2-MariaDB - MariaDB Server
-- SO del servidor:              Win64
-- HeidiSQL Versión:             12.14.0.7165
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Volcando estructura de base de datos para smorgas_kaffet
CREATE DATABASE IF NOT EXISTS `smorgas_kaffet` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci */;
USE `smorgas_kaffet`;

-- Volcando datos para la tabla smorgas_kaffet.tbl_compra: ~7 rows (aproximadamente)
INSERT INTO `tbl_compra` (`Folio`, `Importe_Total`, `Cantidad_Total`, `Hora`, `ID_Modo_Entrega`, `ID_Fecha`, `ID_Mesa`) VALUES
	(1, 64.08, 6, '2025-11-12 08:00:00', 2, 1, 101),
	(5, 100.00, 1, '2025-11-12 08:00:00', 1, 1, 107),
	(6, 900.00, 12, '2025-11-12 08:00:00', 1, 1, 105),
	(7, 20.00, 1, '2025-11-12 08:00:00', 2, 1, 105),
	(8, 20.00, 1, '2025-11-12 08:00:00', 1, 1, 105),
	(9, 20.00, 1, '2025-11-12 08:00:00', 1, 1, 100),
	(25, 100.00, 5, '0000-00-00 00:00:00', 1, 1, 104);

-- Volcando datos para la tabla smorgas_kaffet.tbl_detalle: ~10 rows (aproximadamente)
INSERT INTO `tbl_detalle` (`ID_Detalle`, `Folio`, `ID_Producto`, `Cantidad`, `Precio_Unit`, `Subtotal`) VALUES
	(1, 1, 1030, 6, 10.68, 64.08),
	(8, 5, 1013, 1, 100.00, 0.00),
	(9, 6, 1036, 6, 20.00, 0.00),
	(10, 6, 1008, 6, 150.00, 900.00),
	(11, 7, 1030, 1, 20.00, 0.00),
	(12, 8, 1030, 1, 20.00, 0.00),
	(13, 9, 1030, 1, 20.00, 0.00),
	(31, 25, 1029, 3, 20.00, 0.00),
	(32, 25, 1030, 1, 20.00, 0.00),
	(33, 25, 1029, 1, 20.00, 0.00);

-- Volcando datos para la tabla smorgas_kaffet.tbl_fecha: ~1 rows (aproximadamente)
INSERT INTO `tbl_fecha` (`ID_Fecha`, `Dia`, `Mes`, `Anio`) VALUES
	(1, 12, 11, 2025);

-- Volcando datos para la tabla smorgas_kaffet.tbl_mesa: ~9 rows (aproximadamente)
INSERT INTO `tbl_mesa` (`ID_Mesa`, `Mesa`) VALUES
	(100, '100'),
	(101, '101'),
	(102, '102'),
	(103, '103'),
	(104, '104'),
	(105, '105'),
	(106, '106'),
	(107, '107'),
	(108, '108');

-- Volcando datos para la tabla smorgas_kaffet.tbl_modo_entrega: ~2 rows (aproximadamente)
INSERT INTO `tbl_modo_entrega` (`ID_Modo_Entrega`, `Modo_Entrega`) VALUES
	(1, 'Comedor'),
	(2, 'Llevar');

-- Volcando datos para la tabla smorgas_kaffet.tbl_producto: ~37 rows (aproximadamente)
INSERT INTO `tbl_producto` (`ID_Producto`, `Nombre_Producto`, `Precio_Producto`, `Categoria`) VALUES
	(1000, 'Huevo smorgas', 120.00, 'Especialidad'),
	(1001, 'Huevos criollos', 120.00, 'Especialidad'),
	(1002, 'Huevos ibericos', 120.00, 'Especialidad'),
	(1003, 'Huevos peninsulares', 120.00, 'Especialidad'),
	(1004, 'Omelette del chef', 120.00, 'Especialidad'),
	(1005, 'Omelette jamon y queso', 110.00, 'Especialidad'),
	(1006, 'Omelette papa y chorizo', 110.00, 'Especialidad'),
	(1007, 'Tortilla española', 120.00, 'Especialidad'),
	(1008, 'Huevos pyttipana', 150.00, 'Especialidad'),
	(1009, 'Huevos al gusto', 100.00, 'Especialidad'),
	(1010, 'Panini', 65.00, 'Sandwiches, Baguettes y Varios'),
	(1011, 'Sandwich pan blanco', 95.00, 'Sandwiches, Baguettes y Varios'),
	(1012, 'Sandwich integral', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1013, 'Baguette', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1014, 'Hotcakes', 90.00, 'Sandwiches, Baguettes y Varios'),
	(1015, 'Ensalada de la casa', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1016, 'Burritas', 100.00, 'Sandwiches, Baguettes y Varios'),
	(1017, 'Burritas smorgas', 120.00, 'Sandwiches, Baguettes y Varios'),
	(1018, 'Paquete 1 desayuno sencillo', 150.00, 'Paquetes'),
	(1019, 'Paquete 2 desayuno completo', 180.00, 'Paquetes'),
	(1020, 'Paquete 3 desayuno sencillo de especialidad', 170.00, 'Paquetes'),
	(1021, 'Paquete 4 desayuno completo de especialidad', 200.00, 'Paquetes'),
	(1022, 'Café tipo veracruz', 40.00, 'Bebidas'),
	(1023, 'Café tipo americano', 40.00, 'Bebidas'),
	(1024, 'Café oscuro', 40.00, 'Bebidas'),
	(1025, 'Café descafeinado', 50.00, 'Bebidas'),
	(1026, 'Café tipo cubano', 60.00, 'Bebidas'),
	(1027, 'Café tipo espresso', 80.00, 'Bebidas'),
	(1028, 'Té', 30.00, 'Bebidas'),
	(1029, 'Agua de sandía', 20.00, 'Bebidas'),
	(1030, 'Agua de melón', 20.00, 'Bebidas'),
	(1031, 'Refresco embotellados', 30.00, 'Bebidas'),
	(1032, 'Vaso de leche', 25.00, 'Bebidas'),
	(1033, 'Vaso de leche c/plátano o chocolate', 30.00, 'Bebidas'),
	(1034, 'Postre del día', 25.00, 'Bebidas'),
	(1035, 'Botella de agua', 10.00, 'Bebidas'),
	(1036, 'Ingrediente extra', 20.00, 'Bebidas');

-- Volcando datos para la tabla smorgas_kaffet.tbl_usuarios: ~8 rows (aproximadamente)
INSERT INTO `tbl_usuarios` (`ID_Usuario`, `Nombre_Usuario`, `Rol_Usuario`, `Contrasenia_hash`, `Fecha_Creacion`, `Session_Token`, `Session_Expira`, `Ultimo_Visto`) VALUES
	(1, 'David', 'admin', 'scrypt:32768:8:1$h79DzQeUOmZsTtRH$824965f36dd076eb56db8e34edabc683fdeb89fef96101df14ff56a7b6ba8ad1a8a83a71910a714d890ff2393a6f910b4f4429b55375b80658934d0c9bdf1345', '2025-11-12 08:17:09', NULL, NULL, '2026-03-06 14:57:44'),
	(2, 'shirley', 'mesero', 'scrypt:32768:8:1$AntMIuIFRHa9HkLO$4b06af79a513e32f0e9eaebb6595a1638b9843446ad76c54373ac816f82f075df6dc6ec67ad78fa97d1751809e39f27f12efceedd167d65b85905d59e50d663f', '2025-11-12 08:28:02', NULL, NULL, '2025-11-12 08:30:38'),
	(5, 'Shir', 'mesero', 'scrypt:32768:8:1$ClsJZFw8aSqIx9YK$33565d9d20e24defc28632cf4f3361b6ec86821d6360ffe7fef79a9d65de84ea8a8720278a77ee2afa9f0ecdefe2a477fa529b3ab7ac0898dc720d10e3e5afaf', '2025-11-12 08:31:19', '6542a676362bbaedf722f63ecbb610a8', '2026-03-06 15:16:29', '2026-03-06 14:46:29'),
	(7, 'LissAd', 'admin', 'scrypt:32768:8:1$YgQgADiC6rWI7pdB$4166dc2dc94cf52b88c128e9c776bd29627de3ab8618aa9c1747185917c44239eeefcd6c0f77add10954601e8c096bb98116f232f1ef615de48ca0f5207ace2c', '2025-11-12 08:35:20', NULL, NULL, '2025-11-12 08:47:04'),
	(10, 'Edelmy', 'mesero', 'scrypt:32768:8:1$6ks4wwRb2IVIDhI7$6035564de1b838b1c9a572a3dc0d58e9f982bf80e2783e5cc38d0ca210f3c3a289a7643a42dcc40f269c8464a6a8c83dd64e6466edf03131dbb37660c190c9d6', '2025-11-12 08:40:15', NULL, NULL, '2025-11-12 08:50:07'),
	(11, 'Israel', 'admin', 'scrypt:32768:8:1$Fjl7mJD3ofTrgIpd$d3c48b0e17d9328fd037d108721563e4b5fd779df69ef534dbe403505fb94505b845d5f7be745fe1186a4ea26784b603bfaa427545a22e3c2199e1e30bcb8b30', '2025-11-12 08:50:01', '871184282f139779fae849611bb4cbd5', '2025-11-12 09:20:43', '2025-11-12 08:50:43'),
	(13, 'Janeth', 'mesero', 'scrypt:32768:8:1$WZUd8mbOvvYRQ97F$a5aa4cf202a2e1e34e9ccc982017f077ba7c127e4159a0c07f5ebdb9df43d03cb4867a3ee18451b17386563b9d6538979caf0a58f9a630248448dbe7699caac9', '2026-03-01 11:20:30', '9fc4d11b2f35c0ce6bbd9114a79ba8dd', '2026-03-01 12:12:33', '2026-03-01 11:42:33'),
	(14, 'Emy', 'mesero', 'scrypt:32768:8:1$K11r7VqnKUQg1DtK$9b16b3cc3d2b044edb36815d01ac3a25fa03c2a381ff26612819632b1d93c04b6afac0c7d2e2f51e4421ca2b7ca65952047cb00255bd0ae49d1e7231b375ab9f', '2026-03-06 14:45:02', NULL, NULL, '2026-03-06 14:57:44');

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
