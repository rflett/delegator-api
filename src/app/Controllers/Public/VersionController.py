from os import environ

from flask import Response
from flask_restplus import Namespace, fields

from app.Controllers.Base import RequestValidationController

version_route = Namespace(path="/v", name="Version", description="Returns version information for the server")


@version_route.route("/")
class VersionController(RequestValidationController):
    @version_route.response(200, "Version Info", version_route.model("Version", {"commit_sha": fields.String}))
    def get(self) -> Response:
        """ Returns details of the running application for debugging/verification """
        return self.ok({"commit_sha": environ.get("COMMIT_SHA")})
