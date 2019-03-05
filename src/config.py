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
    REDIS_HOST = "redis"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Local(Config):
    DB_HOST = "localhost"
    REDIS_HOST = "localhost"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Staging(Config):
    DB_HOST = "127.0.0.1"
    REDIS_HOST = "127.0.0.1"
