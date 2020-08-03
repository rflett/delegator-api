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
    PRIVATE_KEY = """
                    LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFcEFJQkFBS0NBUUVBNkdnKy8zUExISlFHdHFpUGJ3WHY1NTRnR
                    WlWZXBKUkh4SHNTc1FURzVKcnVjanBtCkVINlBYSHBBSmg5WjNaMWxjNCtVTityTGpuTzRONy9pWVRrUkQya3Z4M25ZTUhobUJ
                    xVmljNDhSajM4TXVJdkwKUFpXVGx0MElsUkppMEY5a0ZNaVFrSENjQ1JUdGFuU203KytvK0FhYjdrd0NLQ1FEQndab2tESGho
                    OFQ4MCsxZwpiUVdjYURSaTFMZXNMYTQwMzJrVjNTZjBuOTBNSEdRaVhSTmJlN3p5dERwZE90U25VYk9adjlia0NsTTZQQmJ0C
                    nVtVTRGUnpoMng5M29ndVlQeXdCeGZCUE1oTDhubkNqcmdLY2FoYzJJazgwTTlaQ0NBYTE5RkVSQi8zUFdDVU8KRW5HdUp1WG
                    hWRE9udDY5bUNGSWdOWlhuSlhKblBFd0tPSVRHNndJREFRQUJBb0lCQVFERFBWQXZLZ2VucW5NNQpYOEdmYzAxbk50K2FYdXB
                    6T0Y1U0lWSkNnOURTbTVWVlFOb2RZVFR1YTRVWWdaM3RIeHpyUitNc1ZvTksyTXdaCmlZbVVRMnlobGF3ZDE2NVdpYzZzSnF
                    QZWtJSWdHb3VGUFdzd0FVaExwTVJnOTJFcnkvYzN2b1l6MFdaRCt1QzQKWGVjZ0NpWFl0elNuckJManhkMEZPY3o5MWVteE0
                    2R2VyNm1MSnl6REJrbDBYb1VFTFhrODZyQnoyR0llOXpTYQpnWjFFdmtkL3dTZ1FGQmNoUHFKdzl3cHk4aVlETkFndllhb2J
                    4ZWExUk1OMDJIcDdqek5iODVKdW9VNlpwTUpICmZRMTUrQjdXR05sb1Y3dTlaUHhuc1BTU0t2elduUWVVSXEzZHNGVE4zNm9
                    UcVh1M29jVGdnNEw0djU0bUVOOUgKb01sbkpCWUJBb0dCQVBRTXFYdU1Ec0tWSDdiU01FUTZxQmJOU3l6VmJKWkxZcUpaYWU
                    4TkU0T1JPdWt4TWFIbApKYzk5RDVlbEJaczN3NUpaVnZPMVhDZ0pNbjRINE1tTVduWDZnUHg5K1RPaGxLSGxjM0hrTkx2OEp
                    SN2VYeUVtCkFjQ1puM3JGdzM5U21wZ1BFYkVvbWtVUG9uRmd3T1l1akxBYnppU3dYT082SytZSG9TWER6ZmtiQW9HQkFQUEo
                    KbzlQd3U2c2hWUXFxN1RZOVZidjNuUDRYWTNwWDduU3dwWk11UG0zQ3ZWNmR3ckRSNWkxamxtbzJ6bjE0Zm4zVgo2R2VMUDF
                    4bWVrNjU1UFhiNmpPTkJpb1k3ZElvZUpJRVd6V014YzBGS0xOWVBpd2FHaXVFcVFQMit3TUIrSGIyCnZyQ2J1NllhMEU3bk9
                    3a1pzMXJHNS9TeGVoUWh4cGRwTVFaK0xKWnhBb0dBUnlJQnJFOFFaa3JNNlo2dUR0VUIKOVZOMUcrWkJOalZXMUhjM1YwUDZ
                    jaGk4a1FlVHJkcDZnTlcwMjhCdnQrUXpEczhYZHdWZmpSUFJNY2JlRUNEbQpwUWlVM0FOanhWYk5XYnJsUVVjQXorSVlkN3p
                    kQVc1d2lGQyttU3hYWlI4UWpFMm9ISGozTGpYMlpSR01hQXNkCldwOWdJSFYvUGFrZjduWSsxQ0VVUWcwQ2dZQTBwYUlNbmh
                    0WkxKeVo3aW5HSWQ3RzlnVmdWaHEwakJMQi9uZnoKWGZRN2JlZkpiQlprYXgvalEzTnpRcHk3T2U5UEs0ZkIvSzlWUEFoRH
                    doOXcvT29KOGZXWDE4UmNNME0rZlZSWgpMeXAwU1IzdUJTdUFDSzhJSU9FREt5NHdDeGZtVVFrRFNNNXdZN0FDcWlyMG55a
                    zlmR0VSVmRhQVRINy9xY2JkCm1SZjE4UUtCZ1FEYXBtMmJzMGFwMUwxNm82WEZhSXIxaGc1OWZlMGpKRjlaUXp2V0FtRXR2
                    VTE3cDMxRnZvTWkKcUFkTlhreTIwVFZtREJsTnRZekVVVVgrYWVnVFQwRE1pQ3FnZDRNVWUwT3dLRW1DUXJIbnljbEk3RW9
                    qQjJJdApKNm9MWUFLWEtTZHFIT0tlczNYN1J1Z3FIMlgxK1FFa08rWVlKRHV4OWpibzZsZ2hudVJ4RGc9PQotLS0tLUVORC
                    BSU0EgUFJJVkFURSBLRVktLS0tLQo=
    """
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
