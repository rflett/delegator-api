import logging
from os import getenv

import flask_profiler
import sentry_sdk
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from flask import Flask
from flask_cors import CORS
from sentry_sdk.integrations.flask import FlaskIntegration

from app.Apis import api
from app.Config.parameter_store import ParameterStore
from app.Config.secrets_manager import SecretsManager
from app.Extensions.Database import db
from app.Extensions.ErrorHandlers import handle_error
from app.Extensions.Errors import ValidationError
from app.Extensions.Errors import AuthenticationError
from app.Extensions.Errors import AuthorizationError
from app.Extensions.Errors import InternalServerError
from app.Extensions.Errors import ResourceNotFoundError

# flask conf
app = Flask(__name__)
CORS(app)

# config
app_env = getenv("APP_ENV", "Local")
app.config.from_object(f"app.Config.flask_conf.{app_env}")
logging.basicConfig(level=app.config["LOG_LEVEL"])

# get config from parameter store
if app_env not in ["Local", "Docker", "Ci"]:
    # parameter store
    params = ParameterStore().get_params(app_env)
    app.config.update(params)
    # sentry
    sentry_sdk.init(app.config["SENTRY_DSN"], environment=app_env, integrations=[FlaskIntegration()])

# load secrets from aws secrets manager in production (specifically DB creds)
if app_env == "Production":
    secrets = SecretsManager().get_params()
    app.config.update(secrets)

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
