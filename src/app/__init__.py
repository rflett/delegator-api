import logging
from contextlib import contextmanager
from os import getenv

import boto3
import flask_profiler
import sentry_sdk
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from aws_xray_sdk.ext.flask_sqlalchemy.query import XRayFlaskSqlAlchemy
from flask import Flask, url_for
from flask_cors import CORS
from flask_restplus import Api
from sentry_sdk.integrations.flask import FlaskIntegration

from app.ApiWrappers import SubscriptionApi, NotificationApi
from app.Setup.config_ssm import SsmConfig
from app.Setup.config_secretsman import SecretsManConfig

# flask conf and CORS
app = Flask(__name__)
app_env = getenv("APP_ENV", "Local")
app.config.from_object(f"app.Setup.config.{app_env}")
CORS(app)

# get config from parameter store
if app_env not in ["Local", "Docker", "Ci"]:
    # parameter store
    params = SsmConfig().get_params(app_env)
    app.config.update(params)
    # sentry
    sentry_sdk.init(app.config["SENTRY_DSN"], environment=app_env, integrations=[FlaskIntegration()])

# load secrets from aws secrets manager in production (specifically DB creds)
if app_env == "Production":
    secrets = SecretsManConfig().get_params()
    app.config.update(secrets)

# logging
logger = logging.getLogger()
for handler in logger.handlers:
    logger.removeHandler(handler)

log_format = "%(asctime)s delegator-api %(levelname)s %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)


# db conf
app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DB_URI"]
db = XRayFlaskSqlAlchemy(app)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(str(e))
        raise e


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.close()


# aws resources
if getenv("MOCK_AWS"):
    user_settings_table = None
    org_settings_table = None
    user_activity_table = None
    task_activity_table = None
    api_events_sns_topic = None
    email_sns_topic = None
else:
    dyn_db = boto3.resource("dynamodb")
    sns = boto3.resource("sns")
    user_settings_table = dyn_db.Table(app.config["USER_SETTINGS_TABLE"])
    org_settings_table = dyn_db.Table(app.config["ORG_SETTINGS_TABLE"])
    user_activity_table = dyn_db.Table(app.config["USER_ACTIVITY_TABLE"])
    task_activity_table = dyn_db.Table(app.config["TASK_ACTIVITY_TABLE"])
    api_events_sns_topic = sns.Topic(app.config["EVENTS_SNS_TOPIC_ARN"])
    email_sns_topic = sns.Topic(app.config["EMAIL_SNS_TOPIC_ARN"])


# api wrappers
notification_api = NotificationApi(app.config["JWT_SECRET"], app.config["NOTIFICATION_API_PUBLIC_URL"])
subscription_api = SubscriptionApi(app.config["JWT_SECRET"], app.config["SUBSCRIPTION_API_PUBLIC_URL"])


# api docs need to be monkey patched for HTTPS to work
if app_env in ["Staging", "Production"]:

    @property
    def specs_url(self):
        """Monkey patch for HTTPS"""
        return url_for(self.endpoint("specs"), _external=True, _scheme="https")

    Api.specs_url = specs_url

# The API with documentation
api = Api(title="Delegator API", version="1.0", description="The public API for applications.")
# routes
from app.Controllers import all_routes  # noqa

for route in sorted(all_routes, key=lambda x: x.name):
    api.add_namespace(route)

api.init_app(app)

if app_env not in ["Local", "Docker", "Ci"]:
    # flask profiler
    app.config["flask_profiler"] = {
        "enabled": True,
        "storage": {"engine": "sqlalchemy", "db_url": app.config["SQLALCHEMY_DATABASE_URI"]},
        "basicAuth": {"enabled": True, "username": "admin", "password": "B4ckburn3r"},
        "ignore": {"/health/"},
    }
    flask_profiler.init_app(app)


# xray
xray_recorder.configure(
    service="delegator-api",
    context_missing="LOG_ERROR",
    plugins=("ECSPlugin",),
    sampling_rules={
        "version": 2,
        "rules": [
            {
                "description": "Ignore health checks",
                "host": "*",
                "http_method": "*",
                "url_path": "/health/",
                "fixed_target": 0,
                "rate": 0,
            }
        ],
        "default": {"fixed_target": 0, "rate": 0},
    },
)
logging.getLogger("aws_xray_sdk").setLevel(logging.WARNING)
XRayMiddleware(app, xray_recorder)
patch_all()
