from os import environ

from flask import Response

from app import j_response


class VersionController(object):

    @staticmethod
    def get_version_details() -> Response:
        """ Returns details of the running application for debugging/verification """
        return j_response({
            "commit_sha": environ.get('COMMIT_SHA')
        })
