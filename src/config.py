# common settings
class Config(object):
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "DEBUG"
    SIGNUP_ROLE = "ADMIN"
    TOKEN_TTL_IN_MINUTES = 60
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300
    INACTIVE_USER_TTL = 300


class Ci(Config):
    SQLALCHEMY_DATABASE_URI = f"postgresql://backburner:backburner@postgres:5432/backburner"
    R_CACHE_HOST = "redis"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Local(Config):
    SQLALCHEMY_DATABASE_URI = f"postgresql://backburner:backburner@localhost:5432/backburner"
    R_CACHE_HOST = "localhost"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Staging(Config):
    SQLALCHEMY_DATABASE_URI = f"postgresql://backburner:backburner@127.0.0.1:5432/backburner"
    R_CACHE_HOST = "127.0.0.1"
