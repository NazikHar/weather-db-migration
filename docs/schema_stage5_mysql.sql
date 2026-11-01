/*M!999999\- enable the sandbox mode */ 
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `air_quality` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `observation_id` int(11) NOT NULL,
  `carbon_monoxide` double NOT NULL,
  `ozone` double NOT NULL,
  `nitrogen_dioxide` double NOT NULL,
  `sulphur_dioxide` double NOT NULL,
  `pm2_5` double NOT NULL,
  `pm10` double NOT NULL,
  `us_epa_index` int(11) NOT NULL,
  `gb_defra_index` int(11) NOT NULL,
  `is_safe_to_go_outside` tinyint(1) DEFAULT NULL COMMENT 'Чи варто виходити на вулицю: NULL — не обчислено, true/false — так/ні',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_air_quality_observation` (`observation_id`),
  CONSTRAINT `fk_air_quality_observation` FOREIGN KEY (`observation_id`) REFERENCES `weather_observations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=107964 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `weather_observations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `country` varchar(100) NOT NULL,
  `location_name` varchar(100) NOT NULL,
  `last_updated` datetime NOT NULL,
  `temperature_celsius` double NOT NULL,
  `condition_text` varchar(100) NOT NULL,
  `humidity` int(11) NOT NULL,
  `wind_kph` double NOT NULL,
  `wind_degree` int(11) NOT NULL,
  `wind_direction` enum('N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW') NOT NULL,
  `sunrise` time NOT NULL,
  `sunset` time NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_observation` (`country`,`location_name`,`last_updated`),
  KEY `ix_weather_observations_country` (`country`),
  KEY `ix_weather_observations_last_updated` (`last_updated`)
) ENGINE=InnoDB AUTO_INCREMENT=107964 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
