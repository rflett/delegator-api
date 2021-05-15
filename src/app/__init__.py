import logging
from os import getenv

import sentry_sdk
import structlog
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
from app.Extensions.Logging import SetupLogging

SetupLogging()
log = structlog.get_logger()

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

log.info("Finished init")
