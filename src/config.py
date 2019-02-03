# common settings
class Config(object):
    DB_USER = "etemt"
    DB_PASS = "etemt"
    LOG_LEVEL = "DEBUG"
    SIGNUP_ROLE = "ADMIN"
    TOKEN_TTL_IN_MINUTES = 60
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300


class Docker(Config):
    DB_HOST = "postgres"


class Scott(Config):
    SCOTT = "AWESOME"  # can't be empty lol


class Local(Config):
    DB_HOST = "localhost"


class Staging(Config):
    DB_HOST = "postgres"
