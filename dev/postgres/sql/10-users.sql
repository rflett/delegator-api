CREATE TABLE users (
 username VARCHAR (32) UNIQUE NOT NULL PRIMARY KEY,
 password VARCHAR (32) NOT NULL
)
;

INSERT INTO users (username, password)
VALUES ('ryan', 'flett')
;