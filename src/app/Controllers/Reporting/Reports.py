import json
from app import r_cache, j_response, logger
from app.Models.RBAC import Operation, Resource
from flask import request, Response


class Reports(object):
    @staticmethod
    def get_all(request: request) -> Response:
        """
        Get all reports
        :param request:     The request object
        :return:
        """
        from app.Controllers import AuthController
        from app.Models import User

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.GET,
            resource=Resource.REPORTS_PAGE
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            reports = r_cache.hgetall(req_user.org_id)
            logger.info(f"retrieved reports: {json.dumps(reports)}")
            return j_response(reports)
