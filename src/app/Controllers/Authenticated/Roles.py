from flask import Response
from flask_restplus import Namespace
from sqlalchemy import and_

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models.Enums import Operations, Resources
from app.Models.RBAC import Role
from app.Models.Response import message_response_dto
from app.Models.Response.Roles import roles_response

roles_route = Namespace(
    path="/roles",
    name="Roles",
    description="Contains routes for managing user roles"
)


@roles_route.route("/")
class Roles(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.ROLES)
    @roles_route.response(200, "Roles Retrieved", roles_response)
    @roles_route.response(400, "Exception occurred", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Return all roles lower in rank than the requesting user's role. """
        req_user = kwargs['req_user']

        with session_scope() as session:
            # rank > 50 are reserved for admin duties
            roles_qry = session.query(Role).filter(and_(Role.rank >= req_user.roles.rank, Role.rank <= 50)).all()

        roles = [r.as_dict() for r in roles_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.ROLES
        )
        return self.ok({'roles': roles})
