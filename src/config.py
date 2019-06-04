# common settings
class Config(object):
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "DEBUG"
    SIGNUP_ROLE = "ORG_ADMIN"
    TOKEN_TTL_IN_MINUTES = 60
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300
    INACTIVE_USER_TTL = 300
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:008492826001:api-staging-events'
    USER_SETTINGS_TABLE = 'backburner-user-settings-staging'
    ORG_SETTINGS_TABLE = 'backburner-organisation-settings-staging'
    USER_ACTIVITY_TABLE = 'backburner-user-activity-staging'
    TASK_ACTIVITY_TABLE = 'backburner-task-activity-staging'
    REQUEST_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
    RESPONSE_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


class Ci(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://backburner:backburner@postgres:5432/backburner"
    R_CACHE_HOST = "redis"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Local(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://backburner:backburner@localhost:5432/backburner"
    R_CACHE_HOST = "localhost"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5


class Staging(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://backburner:backburner@127.0.0.1:5432/backburner"
    R_CACHE_HOST = "127.0.0.1"
