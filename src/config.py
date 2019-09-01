# common settings
class Config(object):
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "DEBUG"
    SIGNUP_ROLE = "ORG_ADMIN"
    TOKEN_TTL_IN_MINUTES = 72000
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300
    INACTIVE_USER_TTL = 300
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:008492826001:api-staging-events'
    APP_NOTIFICATIONS_SQS = 'https://sqs.ap-southeast-2.amazonaws.com/008492826001/app-notifications-staging'
    USER_SETTINGS_TABLE = 'backburner-user-settings-staging'
    ORG_SETTINGS_TABLE = 'backburner-organisation-settings-staging'
    USER_ACTIVITY_TABLE = 'backburner-user-activity-staging'
    TASK_ACTIVITY_TABLE = 'backburner-task-activity-staging'
    NOTIFICATION_TOKENS_TABLE = 'backburner-notification-tokens-staging'
    REQUEST_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
    RESPONSE_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
    DYN_DB_ACTIVITY_DATE_FORMAT = '%Y%m%dT%H%M%S.%fZ'
    BACKBURNER_API_KEY = 'Skj170raAe2SsWQm4Ny'
    SUBSCRIPTION_API_KEY = 'DWrcxyZsqJ64d1WGUiN'


class Ci(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://backburner:backburner@postgres:5432/backburner"
    R_CACHE_HOST = "redis"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5
    SUBSCRIPTION_API_URL = "http://subscription-api:5001"


class Local(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://backburner:backburner@localhost:5432/backburner"
    R_CACHE_HOST = "localhost"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5
    SUBSCRIPTION_API_URL = "http://localhost:5001"


class Staging(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://backburner:backburner@postgres-staging.backburner:5432/backburner"
    R_CACHE_HOST = "redis-staging.backburner"
    SUBSCRIPTION_API_URL = "https://subscription-api-staging.backburner.online"
