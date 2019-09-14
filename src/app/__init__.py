import logging
from contextlib import contextmanager
from os import getenv

import boto3
import flask_profiler
from flask import Flask
from flask_cors import CORS
from flask_restplus import Api
from flask_sqlalchemy import SQLAlchemy

from app.ApiWrappers import SubscriptionApi

# flask conf
app = Flask(__name__)
app.config.from_object(f"config.{getenv('APP_ENV', 'Local')}")

# flask profiler
app.config["flask_profiler"] = {
    "enabled": True,
    "storage": {
        # "engine": "sqlite"
        "engine": "sqlalchemy",
        "db_url": app.config['SQLALCHEMY_DATABASE_URI']
    },
    "basicAuth": {
        "enabled": True,
        "username": "admin",
        "password": "B4ckburn3r"
    }
}

# CORS
CORS(app)

# logging conf
logger = logging.getLogger()
for handler in logger.handlers:
    logger.removeHandler(handler)

log_format = '%(asctime)s backburner-api %(levelname)s %(message)s'
logging.basicConfig(format=log_format, level=logging.INFO)

# db conf
db = SQLAlchemy(app)

# dynamo db
dyn_db = boto3.resource('dynamodb')
user_settings_table = dyn_db.Table(app.config['USER_SETTINGS_TABLE'])
org_settings_table = dyn_db.Table(app.config['ORG_SETTINGS_TABLE'])
user_activity_table = dyn_db.Table(app.config['USER_ACTIVITY_TABLE'])
task_activity_table = dyn_db.Table(app.config['TASK_ACTIVITY_TABLE'])
notification_tokens_table = dyn_db.Table(app.config['NOTIFICATION_TOKENS_TABLE'])

# sns
sns = boto3.resource('sns')
api_events_sns_topic = sns.Topic(app.config['EVENTS_SNS_TOPIC_ARN'])

# sqs
sqs = boto3.resource('sqs')
app_notifications_sqs = sqs.Queue(app.config['APP_NOTIFICATIONS_SQS'])

# api wrappers
subscription_api = SubscriptionApi(
    url=app.config['SUBSCRIPTION_API_URL'],
    key=app.config['SUBSCRIPTION_API_KEY']
)


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


# The API with documentation
api = Api(
    title="Backburner API",
    version="1.0",
    description="The public API for applications."
)
# routes
from app.Controllers import all_routes  # noqa
for route in all_routes:
    api.add_namespace(route)

api.init_app(app)

if getenv('APP_ENV') not in ['Ci', 'Local']:
    flask_profiler.init_app(app)
