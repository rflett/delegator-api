from app.Models.RBAC import Role
from app.Models.RBAC.Permission import Permission
from app import DBSession
from sqlalchemy import exists

session = DBSession()


class RoleController(object):
    @staticmethod
    def list_roles() -> list:
        """ Returns a list of roles as dicts """
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
        """ Check to see if a {role} can perform {operation} on {resource}. """
        return session.query(session.query(Permission).filter(
            Permission.role_id == role,
            Permission.operation_id == operation,
            Permission.resource_id == resource
        ).exists()).scalar()
