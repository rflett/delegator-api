from os import environ

from flask import Response

from app.Controllers.Base import RequestValidationController


class VersionController(RequestValidationController):
    def get_version_details(self) -> Response:
        """ Returns details of the running application for debugging/verification """
        return self.ok({
            "commit_sha": environ.get('COMMIT_SHA')
        })
