import json
from app.Models.RBAC import Role
from app.Models.RBAC.Permission import Permission
from app import session, logger


class RoleController(object):
    @staticmethod
    def list_roles() -> list:
        """
        Gets all roles from the database, returns them as a list of dicts like:
            {
                "id": "ADMIN",
                "name": "Admin",
                "description": "This role can do anything"
            }
        :return: List of roles.
        """
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
    def role_can(role: str, operation: str, resource: str) -> bool:
        """
        Check to see if a {role} can perform {operation} on {resource}. All it needs to do
        is check to see if the role permission exists in the database.
        :param role:        The role
        :param operation:   The operation to perform
        :param resource:    The resource that will be affected
        :return: True or False
        """
        if role == 'ADMIN':
            logger.debug('role check was performed against ADMIN, allowing all actions')
            return True
        return session.query(session.query(Permission).filter(
            Permission.role_id == role,
            Permission.operation_id == operation,
            Permission.resource_id == resource
        ).exists()).scalar()
