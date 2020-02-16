from os import environ

from flask_restx import Namespace, fields, Resource

api = Namespace(path="/v", name="Version", description="View API version info")


@api.route("/")
class Version(Resource):
    @api.marshal_with(api.model("Version Info", {"commit_sha": fields.String}, code=200))
    def get(self):
        """Returns details of the running application for debugging/verification"""
        return {"commit_sha": environ.get("COMMIT_SHA")}, 200
