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
    # TODO these will be phased out in favour of JWTs
    DELEGATOR_API_KEY = 'Skj170raAe2SsWQm4Ny'
    SUBSCRIPTION_API_KEY = 'DWrcxyZsqJ64d1WGUiN'
    NOTIFICATION_API_KEY = 'JnQqvTV7iGABve1T87K'


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
    JWT_SECRET = '12a516f4e7b99441dba0231deb6fc0c87e2a84ae8beff7f64f6a5ac07058a3ae'


class Docker(Dev):
    """Used when running with docker-compose"""
    SQLALCHEMY_DATABASE_URI = "postgresql://delegator:delegator@postgres:5432/delegator"
    SUBSCRIPTION_API_PUBLIC_URL = "http://subscription-api:5001"
    NOTIFICATION_API_PUBLIC_URL = "http://notification-api:5002"


class Local(Dev):
    """When running on the local machine"""
    SQLALCHEMY_DATABASE_URI = "postgresql://delegator:delegator@127.0.0.1:5432/delegator"
    SUBSCRIPTION_API_PUBLIC_URL = "http://localhost:5001"
    NOTIFICATION_API_PUBLIC_URL = "http://localhost:5002"


class Staging(Config):
    """Staging ECS"""
    EVENTS_SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-2:239304980652:api-staging-events'
    USER_SETTINGS_TABLE = 'user-settings-staging'
    ORG_SETTINGS_TABLE = 'organisation-settings-staging'
    USER_ACTIVITY_TABLE = 'user-activity-staging'
    TASK_ACTIVITY_TABLE = 'task-activity-staging'
