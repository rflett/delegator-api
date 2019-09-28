# common settings
class Config(object):
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "DEBUG"
    SIGNUP_ROLE = "ORG_ADMIN"
    TOKEN_TTL_IN_MINUTES = 72000
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300
    INACTIVE_USER_TTL = 300
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:239304980652:api-dev-events'
    APP_NOTIFICATIONS_SQS = 'https://sqs.ap-southeast-2.amazonaws.com/239304980652/app-notifications-dev'
    USER_SETTINGS_TABLE = 'user-settings-dev'
    ORG_SETTINGS_TABLE = 'organisation-settings-dev'
    USER_ACTIVITY_TABLE = 'user-activity-dev'
    TASK_ACTIVITY_TABLE = 'task-activity-dev'
    REQUEST_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
    RESPONSE_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
    DYN_DB_ACTIVITY_DATE_FORMAT = '%Y%m%dT%H%M%S.%fZ'
    DELEGATOR_API_KEY = 'Skj170raAe2SsWQm4Ny'
    SUBSCRIPTION_API_KEY = 'DWrcxyZsqJ64d1WGUiN'
    JWT_SECRET = '12a516f4e7b99441dba0231deb6fc0c87e2a84ae8beff7f64f6a5ac07058a3ae'


class Docker(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://delegator:delegator@postgres:5432/delegator"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5
    SUBSCRIPTION_API_URL = "http://subscription-api:5001"


class Ci(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://delegator:delegator@127.0.0.1:5432/delegator"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5
    SUBSCRIPTION_API_URL = "https://subscription-api-staging.backburner.online"


class Local(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://delegator:delegator@localhost:5432/delegator"
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5
    SUBSCRIPTION_API_URL = "http://localhost:5001"


class Staging(Config):
    # this should be retreived from SecretsManager instead
    SQLALCHEMY_DATABASE_URI = "postgresql://delegator:k!.]O*;3?j`lg!0J@" \
                              "delegator-staging.cczlgulpiuef.ap-southeast-2.rds.amazonaws.com:5432/delegator"
    SUBSCRIPTION_API_URL = "https://subscription-api-staging.backburner.online"
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:239304980652:api-staging-events'
    APP_NOTIFICATIONS_SQS = 'https://sqs.ap-southeast-2.amazonaws.com/239304980652/app-notifications-staging'
    USER_SETTINGS_TABLE = 'user-settings-staging'
    ORG_SETTINGS_TABLE = 'organisation-settings-staging'
    USER_ACTIVITY_TABLE = 'user-activity-staging'
    TASK_ACTIVITY_TABLE = 'task-activity-staging'
