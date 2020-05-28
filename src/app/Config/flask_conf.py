class Config(object):
    """Common settings"""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PROPAGATE_EXCEPTIONS = True
    LOG_LEVEL = "INFO"
    SIGNUP_ROLE = "ORG_ADMIN"
    TOKEN_TTL_IN_MINUTES = 72000
    FAILED_LOGIN_ATTEMPTS_MAX = 5
    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 300
    INACTIVE_USER_TTL = 300
    REQUEST_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
    RESPONSE_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    DYN_DB_ACTIVITY_DATE_FORMAT = "%Y%m%dT%H%M%S.%fZ"
    SENTRY_DSN = "https://1b44956bd3544f70b7ae66f0c126b76f@sentry.io/1881906"
    ASSETS_BUCKET = "assets.delegator.com.au"
    ASSETS_DISTRIBUTION_ID = "EZPY1QFZCY2Y6"


class Dev(Config):
    """Common to development environments"""

    FAILED_LOGIN_ATTEMPTS_TIMEOUT = 5
    EVENTS_SNS_TOPIC_ARN = "arn:aws:sns:ap-southeast-2:239304980652:api-dev-events"
    EMAIL_SNS_TOPIC_ARN = "arn:aws:sns:ap-southeast-2:239304980652:email-sender-dev"
    USER_SETTINGS_TABLE = "user-settings-dev"
    ORG_SETTINGS_TABLE = "organisation-settings-dev"
    USER_ACTIVITY_TABLE = "user-activity-dev"
    TASK_ACTIVITY_TABLE = "task-activity-dev"
    # the following are retrieved from SSM parameter store in higher envs
    CONTACT_US_GOOGLE_RECAPTCHA_SECRET = "6Lfmlt4UAAAAAL1nG0CyxtRmoC2o0UjlIpljau1K"
    PUBLIC_WEB_URL = "http://localhost:4200"
    JWT_SECRET = "dev_s3cr3t"
    XRAY_RULE_IGNORE_HEALTH = "{}"
    WEBSITE_URL = "staging.delegator.com.au"


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

    EVENTS_SNS_TOPIC_ARN = "arn:aws:sns:ap-southeast-2:239304980652:api-staging-events"
    EMAIL_SNS_TOPIC_ARN = "arn:aws:sns:ap-southeast-2:239304980652:email-sender-staging"
    USER_SETTINGS_TABLE = "user-settings-staging"
    ORG_SETTINGS_TABLE = "organisation-settings-staging"
    USER_ACTIVITY_TABLE = "user-activity-staging"
    TASK_ACTIVITY_TABLE = "task-activity-staging"
    WEBSITE_URL = "staging.delegator.com.au"


class Production(Config):
    """Production ECS"""

    EVENTS_SNS_TOPIC_ARN = "arn:aws:sns:ap-southeast-2:239304980652:api-production-events"
    EMAIL_SNS_TOPIC_ARN = "arn:aws:sns:ap-southeast-2:239304980652:email-sender-production"
    USER_SETTINGS_TABLE = "user-settings-production"
    ORG_SETTINGS_TABLE = "organisation-settings-production"
    USER_ACTIVITY_TABLE = "user-activity-production"
    TASK_ACTIVITY_TABLE = "task-activity-production"
    WEBSITE_URL = "delegator.com.au"
