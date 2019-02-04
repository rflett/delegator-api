import json
import typing
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
    engine = create_engine(f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{db_ip}/etemt")
else:
    engine = create_engine(
        f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{app.config['DB_HOST']}/etemt")

# database session and base
DBSession = sessionmaker(bind=engine)
DBBase = declarative_base()
session = DBSession()


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
    # default headers
    headers = {'Content-Type': 'application/json'}

    # merge new headers if there are any
    if kwargs.get('headers') is not None:
        headers = {
            **headers,
            **kwargs.pop('headers')
        }

    return Response(
        json.dumps({
            "msg": msg
        }),
        status=status,
        headers=headers,
        **kwargs
    )


# routes
from app import routes   # noqa
