import json
import typing
from app.Models.RBAC import Role, Operation, Resource
from app.Models.RBAC.Permission import Permission
from app import logger, session_scope
from flask import request, Response


def _get_role(role_id: str) -> Role:
    with session_scope() as session:
        role = session.query(Role).filter(Role.id == role_id).first()
        return role


class RoleController(object):
    @staticmethod
    def get_roles(request: request) -> Response:
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
            user_role = _get_role(req_user.role)

            with session_scope() as session:
                roles_qry = session.query(Role).filter(Role.rank >= user_role.rank).all()

            roles = [r.as_dict() for r in roles_qry]

            logger.debug(f"retrieved {len(roles)} roles: {json.dumps(roles)}")
            return Response(json.dumps(roles), status=200, headers={"Content-Type": "application/json"})

    @staticmethod
    def list_roles() -> list:
        """
        Gets all roles from the database, returns them as a list of dicts like:
            {
                "id": "ADMIN",
                "rank": 1,
                "name": "Admin",
                "description": "This role can do anything"
            }
        :return: List of roles.
        """
        with session_scope() as session:
            roles_qry = session.query(Role).all()

        roles = []

        # get dict for each role and just get the id, name and desc
        for r in roles_qry:
            qry_role_dict = r.__dict__
            return_role_dict = {
                'id': qry_role_dict.get('id'),
                'name': qry_role_dict.get('name'),
                'description': qry_role_dict.get('description')
            }
            roles.append(return_role_dict)

        logger.debug(f"retrieved {len(roles)} roles: {json.dumps(roles)}")

        return roles

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
        # check permission exists
        with session_scope() as session:
            exists = session.query(session.query(Permission).filter(
                Permission.role_id == role,
                Permission.operation_id == operation,
                Permission.resource_id == resource
            ).exists()).scalar()

        if exists:
            with session_scope() as session:
                permission = session.query(Permission).filter(
                    Permission.role_id == role,
                    Permission.operation_id == operation,
                    Permission.resource_id == resource
                ).first()
                return permission.resource_scope
        else:
            return False
