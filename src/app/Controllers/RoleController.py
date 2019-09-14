from flask import Response
from sqlalchemy import and_

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Models.Enums import Operations, Resources
from app.Models.RBAC import Role


class RoleController(RequestValidationController):
    def get_roles(self, **kwargs) -> Response:
        """Return all roles lower in rank than the requesting user's role. """
        req_user = kwargs['req_user']

        with session_scope() as session:
            # rank > 99 are reserved for admin duties
            roles_qry = session.query(Role).filter(and_(Role.rank >= req_user.roles.rank, Role.rank <= 99)).all()

        roles = [r.as_dict() for r in roles_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.ROLES
        )
        return self.ok(roles)
