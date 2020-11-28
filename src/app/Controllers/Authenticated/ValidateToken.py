import structlog
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt

api = Namespace(path="/validate", name="Validate", description="Validate the User's token")
log = structlog.getLogger()


class NullableString(fields.String):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "nullable string"


@api.route("/")
class ValidationChecker(RequestValidationController):

    @requires_jwt
    @api.response(204, "Token Valid")
    def get(self, **kwargs):
        """Runs the auth token past the middleware, returns a 204 if the token is valid"""
        return "", 204
