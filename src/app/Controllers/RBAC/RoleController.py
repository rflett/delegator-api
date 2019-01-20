from app.Models.RBAC import Role
from app.Models.RBAC.Permission import Permission
from app import DBSession
from sqlalchemy import exists

session = DBSession()


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

        return roles

    @staticmethod
    def role_can(role: str, operation: str, resource: str) -> bool:
        """ 
        Check to see if a {role} can perform {operation} on {resource}. All it needs to do
        is check to see if the role permission exists in the database.

        :param role str:        The role
        :param operation str:   The operation to perform
        :param resource str:    The resource that will be affected
        
        :return: True or False
        """
        return session.query(session.query(Permission).filter(
            Permission.role_id == role,
            Permission.operation_id == operation,
            Permission.resource_id == resource
        ).exists()).scalar()
