import json
from app import r_cache, j_response, logger
from app.Models.RBAC import Operation, Resource
from flask import request, Response


class Reports(object):
    @staticmethod
    def get_all(req: request) -> Response:
        """ Get all reports """
        from app.Controllers import AuthController

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.REPORTS_PAGE
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        reports = r_cache.hgetall(req_user.org_id)
        logger.debug(f"retrieved reports: {json.dumps(reports)}")
        return j_response(reports)
