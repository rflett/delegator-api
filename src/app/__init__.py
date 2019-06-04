import json
import logging
import typing
from contextlib import contextmanager
from logging.handlers import SysLogHandler
from os import getenv

import boto3
import flask_profiler
import redis
from flask import Flask, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

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
log_handler = SysLogHandler()
log_handler.setLevel(app.config['LOG_LEVEL'])
app.logger.addHandler(log_handler)
logger = app.logger

# gunicorn logging
if getenv('APP_ENV', 'Local') != 'Local':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# redis conf
r_cache = redis.Redis(host=app.config['R_CACHE_HOST'], port=6379, db=0, charset="utf-8", decode_responses=True)

# db conf
db = SQLAlchemy(app)

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


# json response object
def j_response(body: typing.Optional[typing.Union[dict, list]] = None, status: int = 200, **kwargs) -> Response:
    """
    Just a Flask Response but it provides a nice wrapper for returning generic json responses, so that they
    easily remain consistent.
    :param body:    The dict to send as a json body
    :param status:  The HTTP status for the Response
    :param kwargs:  Other Flask Response object kwargs (like headers etc.)
    :return:        A flask response
    """
    # default headers
    headers = {'Content-Type': 'application/json'}

    # merge new headers if there are any
    if kwargs.get('headers') is not None:
        headers = {
            **headers,
            **kwargs.pop('headers')
        }

    if body is None:
        return Response(
            status=204,
            headers=headers,
            **kwargs
        )
    else:
        return Response(
            json.dumps(body),
            status=status,
            headers=headers,
            **kwargs
        )


# generic response object
def g_response(msg: typing.Optional[str] = None, status: int = 200, **kwargs) -> Response:
    """
    Just a Flask Response but gives one place to define a consistent response to use for generic responses
    throughout the application.
    :param msg:     The message to send as part of the "msg" key
    :param status:  The HTTP status for the Response
    :param kwargs:  Other Flask Response object kwargs (such as headers, status etc.)
    :return:        A Flask Response
    """
    return j_response(
        {"msg": msg},
        status=status,
        **kwargs
    )


# routes
from app import routes  # noqa

if getenv('APP_ENV') != 'Ci':
    flask_profiler.init_app(app)
