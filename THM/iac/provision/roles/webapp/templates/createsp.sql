use {{ db_name }};

drop PROCEDURE IF EXISTS `sp_createUser`;

DELIMITER $$
CREATE PROCEDURE `sp_createUser`(
    IN p_name VARCHAR(20),
    IN p_username VARCHAR(20),
    IN p_password VARCHAR(162)
)
BEGIN
    if ( select exists (select 1 from tbl_user where user_username = p_username) ) THEN
        select 'Username Exists !!';
    ELSE
        insert into tbl_user
        (
            user_name,
            user_username,
            user_password
        )
        values
        (
            p_name,
            p_username,
            p_password
        );
    END IF;
END$$
DELIMITER ;

drop PROCEDURE IF EXISTS `sp_validateLogin`;

DELIMITER $$
CREATE PROCEDURE `sp_validateLogin`(
IN p_username VARCHAR(20)
)
BEGIN
    select * from tbl_user where user_username = p_username;
END$$
DELIMITER ;