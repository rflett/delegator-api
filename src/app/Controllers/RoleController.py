from flask import request, Response
from sqlalchemy import and_

from app import session_scope, j_response
from app.Models.Enums import Operations, Resources


class RoleController(object):
    @staticmethod
    def get_roles(req: request) -> Response:
        """Return all roles lower in rank than the requesting user's role. """
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
        return j_response(roles)
