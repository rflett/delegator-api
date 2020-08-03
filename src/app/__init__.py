import logging
from os import getenv

import sentry_sdk
import structlog
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from flask import Flask
from flask_cors import CORS
from sentry_sdk.integrations.flask import FlaskIntegration

from app.Apis import api
from app.Config.parameter_store import ParameterStore
from app.Extensions.Database import db
from app.Extensions.ErrorHandlers import handle_error
from app.Extensions.Errors import ValidationError
from app.Extensions.Errors import AuthenticationError
from app.Extensions.Errors import AuthorizationError
from app.Extensions.Errors import InternalServerError
from app.Extensions.Errors import ResourceNotFoundError

app_env = getenv("APP_ENV", "Local")
log = structlog.get_logger()


def env_injector(_, __, event_dict):
    event_dict["environment"] = app_env.lower()
    return event_dict


# flask conf
app = Flask(__name__)
CORS(app)

# config
app.config.from_object(f"app.Config.flask_conf.{app_env}")
logging.basicConfig(level=app.config["LOG_LEVEL"])

# get config from parameter store
if app_env not in ["Local", "Docker", "Ci"]:
    # parameter store
    params = ParameterStore().get_params(app_env)
    app.config.update(params)
    # sentry
    sentry_sdk.init(app.config["SENTRY_DSN"], environment=app_env, integrations=[FlaskIntegration()])
    # logging
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        env_injector,
        structlog.processors.TimeStamper(fmt="iso", key="time"),
        structlog.processors.JSONRenderer(),
    ]
else:
    # logging
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        env_injector,
        structlog.processors.TimeStamper(fmt="%H:%M:%S", key="time", utc=False),
        structlog.dev.ConsoleRenderer(),
    ]

structlog.configure(processors=processors, cache_logger_on_first_use=True)
log.info("Starting init")

# db conf
app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DB_URI"]
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db.init_app(app)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.close()


# add the api and its namespaces to the app
api.init_app(app)

# register error handlers
app.register_error_handler(ValidationError, handle_error)
app.register_error_handler(AuthenticationError, handle_error)
app.register_error_handler(AuthorizationError, handle_error)
app.register_error_handler(ResourceNotFoundError, handle_error)
app.register_error_handler(InternalServerError, handle_error)

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

log.info("Finished init")
