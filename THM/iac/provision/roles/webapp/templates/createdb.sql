drop DATABASE IF EXISTS {{ db_name }};

CREATE DATABASE {{ db_name }};

USE {{ db_name }};

drop TABLE IF EXISTS `tbl_user`;

CREATE TABLE `{{ db_name }}`.`tbl_user` (
  `user_id` BIGINT AUTO_INCREMENT,
  `user_name` VARCHAR(45) NULL,
  `user_username` VARCHAR(45) NULL,
  `user_password` VARCHAR(162) NULL,
  PRIMARY KEY (`user_id`));
