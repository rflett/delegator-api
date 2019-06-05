import json

from flask import request, Response
from sqlalchemy import and_

from app import logger, session_scope, j_response
from app.Models.Enums import Operations, Resources


class RoleController(object):
    @staticmethod
    def get_roles(req: request) -> Response:
        """
        Returns a list of roles. Any user can call this route, but only roles that have a rank
        greater than theirs will be returned. For example, and admin would be rank 1 so can get all roles,
        but a middle level role can only get roles with less permissions than them.
        """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import User
        from app.Models.RBAC import Role

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.ROLES
        )

        with session_scope() as session:
            roles_qry = session.query(Role)\
                .filter(
                    Role.rank >=
                    session.query(Role.rank)
                    .join(User.roles)
                    .filter(
                        and_(
                            User.id == req_user.id,
                            Role.id == req_user.role
                        )
                    )
                ).all()

        roles = [r.as_dict() for r in roles_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.ROLES
        )
        logger.debug(f"found {len(roles)} roles: {json.dumps(roles)}")
        return j_response(roles)