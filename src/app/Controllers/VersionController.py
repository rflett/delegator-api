import json
from app import g_response
from flask import Response
from os import environ


class VersionController(object):

    @staticmethod
    def get_version_details() -> Response:
        """
        Returns details of the running application for debugging/verification
        :return: Response containing application info
        """
        ret = {
            "commit_sha": environ.get('COMMIT_SHA')
        }
        return g_response(json.dumps(ret))
