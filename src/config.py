class Config(object):
    """Common settings"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "DEBUG"
    SIGNUP_ROLE = "ORG_ADMIN"
    TOKEN_TTL_IN_MINUTES = 72000
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300
    INACTIVE_USER_TTL = 300
    REQUEST_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
    RESPONSE_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
    DYN_DB_ACTIVITY_DATE_FORMAT = '%Y%m%dT%H%M%S.%fZ'


class Dev(Config):
    """Common to development environments"""
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:239304980652:api-dev-events'
    USER_SETTINGS_TABLE = 'user-settings-dev'
    ORG_SETTINGS_TABLE = 'organisation-settings-dev'
    USER_ACTIVITY_TABLE = 'user-activity-dev'
    TASK_ACTIVITY_TABLE = 'task-activity-dev'
    # the following are retrieved from SSM parameter store in higher envs
    PUBLIC_WEB_URL = "http://localhost:4200/"
    JWT_SECRET = 'dev_s3cr3t'


class Docker(Dev):
    """Used when running with docker-compose"""
    DB_URI = "postgresql://delegator:delegator@postgres:5432/delegator"
    SUBSCRIPTION_API_PUBLIC_URL = "http://subscription-api:5001"
    NOTIFICATION_API_PUBLIC_URL = "http://notification-api:5002"


class Local(Dev):
    """When running on the local machine"""
    DB_URI = "postgresql://delegator:delegator@127.0.0.1:5432/delegator"
    SUBSCRIPTION_API_PUBLIC_URL = "http://localhost:5001"
    NOTIFICATION_API_PUBLIC_URL = "http://localhost:5002"


class Staging(Config):
    """Staging ECS"""
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:239304980652:api-staging-events'
    USER_SETTINGS_TABLE = 'user-settings-staging'
    ORG_SETTINGS_TABLE = 'organisation-settings-staging'
    USER_ACTIVITY_TABLE = 'user-activity-staging'
    TASK_ACTIVITY_TABLE = 'task-activity-staging'


class Production(Config):
    """Production ECS"""
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:239304980652:api-production-events'
    USER_SETTINGS_TABLE = 'user-settings-production'
    ORG_SETTINGS_TABLE = 'organisation-settings-production'
    USER_ACTIVITY_TABLE = 'user-activity-production'
    TASK_ACTIVITY_TABLE = 'task-activity-production'
