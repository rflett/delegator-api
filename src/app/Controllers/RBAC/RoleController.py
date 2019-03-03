import json
import typing
from app.Models.RBAC import Role, Operation, Resource
from app.Models.RBAC.Permission import Permission
from app import logger, session_scope, j_response
from flask import request, Response


class RoleController(object):
    @staticmethod
    def get_roles(request: request) -> Response:
        """
        Returns a list of roles. Any use can call this route, but only roles that have a rank
        greater than theirs will be returned. For example, and admin would be rank 1 so can get all roles,
        but a middle level role can only get roles with less permissions than them.
        :param request: The request
        :return:        A list of roles
        """
        from app.Controllers import AuthController
        from app.Models import User
        from app.Models.RBAC import Role

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.GET,
            resource=Resource.ROLE
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            with session_scope() as session:
                roles_qry = session.query(Role)\
                    .filter(Role.rank >=
                            session.query(Role.rank)
                            .join(User.roles)
                            .filter(Role.id == req_user.role)
                            )\
                    .all()

            roles = [r.as_dict() for r in roles_qry]

            logger.info(f"got {len(roles)} roles: {json.dumps(roles)}")
            return j_response(roles)

    @staticmethod
    def role_can(role: str, operation: str, resource: str) -> typing.Union[bool, str]:
        """
        Check to see if a {role} can perform {operation} on {resource}. All it needs to do
        is check to see if the role permission exists in the database.
        :param role:        The role
        :param operation:   The operation to perform
        :param resource:    The resource that will be affected
        :return: True or False
        """
        with session_scope() as session:
            permission = session.query(Permission).filter(
                Permission.role_id == role,
                Permission.operation_id == operation,
                Permission.resource_id == resource
            ).first()
            if permission is None:
                logger.info(f"permission with role:{role}, operation:{operation}, resource:{resource} does not exist")
                return False
            else:
                return permission.resource_scope
