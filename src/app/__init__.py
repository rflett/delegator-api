import json
import logging
from contextlib import contextmanager
from os import getenv

import boto3
import flask_profiler
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from aws_xray_sdk.ext.flask_sqlalchemy.query import XRayFlaskSqlAlchemy
from flask import Flask, url_for
from flask_cors import CORS
from flask_restplus import Api

from config_ssm import SsmConfig
from config_secretsman import SecretsManConfig
from app.ApiWrappers import SubscriptionApi, NotificationApi

# flask conf
app = Flask(__name__)
app_env = getenv('APP_ENV', 'Local')
app.config.from_object(f"config.{app_env}")

# load in values from parameter store in higher envs
if app_env not in ['Local', 'Docker', 'Ci']:
    # parameter store
    params = SsmConfig().get_params(app_env)
    app.config.update(params)

# load secrets from aws secrets manager in production
if app_env == 'Production':
    secrets = SecretsManConfig().get_params()
    app.config.update(secrets)

app.config['SQLALCHEMY_DATABASE_URI'] = app.config['DB_URI']

# xray
xray_recorder.configure(
    service='delegator-api',
    context_missing='LOG_ERROR',
    plugins=("ECSPlugin",),
    sampling_rules=json.loads(app.config['XRAY_RULE_IGNORE_HEALTH'])
)
XRayMiddleware(app, xray_recorder)
logging.getLogger('aws_xray_sdk').setLevel(logging.WARNING)

# flask profiler
app.config["flask_profiler"] = {
    "enabled": True,
    "storage": {
        "engine": "sqlalchemy",
        "db_url": app.config['SQLALCHEMY_DATABASE_URI']
    },
    "basicAuth": {
        "enabled": True,
        "username": "admin",
        "password": "B4ckburn3r"
    },
    "ignore": {
        "/health/"
    }
}

# CORS
CORS(app)

# logging conf
logger = logging.getLogger()
for handler in logger.handlers:
    logger.removeHandler(handler)

log_format = '%(asctime)s delegator-api %(levelname)s %(message)s'
logging.basicConfig(format=log_format, level=logging.INFO)

# db conf
db = XRayFlaskSqlAlchemy(app)

if getenv('MOCK_AWS'):
    user_settings_table = None
    org_settings_table = None
    user_activity_table = None
    task_activity_table = None
    api_events_sns_topic = None
else:
    # dynamo db
    dyn_db = boto3.resource('dynamodb')
    user_settings_table = dyn_db.Table(app.config['USER_SETTINGS_TABLE'])
    org_settings_table = dyn_db.Table(app.config['ORG_SETTINGS_TABLE'])
    user_activity_table = dyn_db.Table(app.config['USER_ACTIVITY_TABLE'])
    task_activity_table = dyn_db.Table(app.config['TASK_ACTIVITY_TABLE'])
    # sns
    sns = boto3.resource('sns')
    api_events_sns_topic = sns.Topic(app.config['EVENTS_SNS_TOPIC_ARN'])


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


# api wrappers
notification_api = NotificationApi(app.config['JWT_SECRET'], app.config['NOTIFICATION_API_PUBLIC_URL'])
subscription_api = SubscriptionApi(app.config['JWT_SECRET'], app.config['SUBSCRIPTION_API_PUBLIC_URL'])


if app_env in ['Staging', 'Production']:
    @property
    def specs_url(self):
        """Monkey patch for HTTPS"""
        return url_for(self.endpoint('specs'), _external=True, _scheme='https')

    Api.specs_url = specs_url

# The API with documentation
api = Api(
    title="Delegator API",
    version="1.0",
    description="The public API for applications."
)
# routes
from app.Controllers import all_routes  # noqa
for route in sorted(all_routes, key=lambda x: x.name):
    api.add_namespace(route)

api.init_app(app)

# xray
patch_all()


if app_env not in ['Local', 'Docker', 'Ci']:
    # flask profiler
    flask_profiler.init_app(app)
