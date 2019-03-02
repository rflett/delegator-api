# common settings
class Config(object):
    DB_USER = "backburner"
    DB_PASS = "backburner"
    LOG_LEVEL = "DEBUG"
    SIGNUP_ROLE = "ADMIN"
    TOKEN_TTL_IN_MINUTES = 60
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300
    INACTIVE_USER_TTL = 300


class Ci(Config):
    DB_HOST = "postgres"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Scott(Config):
    SCOTT = "AWESOME"  # can't be empty lol


class Local(Config):
    DB_HOST = "localhost"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Staging(Config):
    DB_HOST = "postgres"
