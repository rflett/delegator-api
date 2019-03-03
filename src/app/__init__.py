import json
import logging
import typing
from contextlib import contextmanager
from flask import Flask, Response
from flask_cors import CORS
from logging.handlers import SysLogHandler
from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# flask conf
app = Flask(__name__)
app.config.from_object(f"config.{getenv('APP_ENV', 'Local')}")

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

# db conf
if getenv('APP_ENV') == 'Scott':
    import boto3
    # scott's access token, don't do this
    ec2 = boto3.client('ec2')
    api_staging = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    'api-staging',
                ]
            },
        ]
    )
    db_ip = api_staging.get('Reservations')[0].get('Instances')[0].get('PublicIpAddress')
    engine = create_engine(f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{db_ip}/backburner")
else:
    engine = create_engine(
        f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{app.config['DB_HOST']}/backburner")

# database session and base
DBSession = sessionmaker(bind=engine)
DBBase = declarative_base()
session = DBSession()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(str(e))
        raise e


@app.teardown_appcontext
def shutdown_session(exception=None):
    session.close()


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
        json.dumps({
            "msg": msg
        }),
        status=status,
        **kwargs
    )


# routes
from app import routes   # noqa
