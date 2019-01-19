import binascii
import datetime
import hashlib
import os
from app import DBBase, DBSession
from app.Controllers.RBAC.RoleController import RoleController
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

session = DBSession()


def _hash_password(password: str) -> str:
    """ Hash a password for storing. See https://www.vitoshacademy.com/hashing-passwords-in-python/"""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def _get_jwt_secret(org_id: int) -> str:
    """ Gets the JWT secret for this users organisation """
    from app.Controllers import OrganisationController
    user_org = OrganisationController.get_org_by_id(org_id)
    return user_org.jwt_secret


def _get_jwt_aud(org_id: int) -> str:
    """ Gets the JWT aud for this users organisation """
    from app.Controllers import OrganisationController
    user_org = OrganisationController.get_org_by_id(org_id)
    return user_org.jwt_aud


class User(DBBase):
    __tablename__ = "users"

    id = Column('id', Integer(), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    username = Column('username', String())
    email = Column('email', String())
    first_name = Column('first_name', String())
    last_name = Column('last_name', String())
    password = Column('password', String())
    role = Column('role', String(), ForeignKey('rbac_roles.id'))
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    org_r = relationship("Organisation")
    role_r = relationship("Role")

    def __init__(
            self,
            org_id: int,
            username: str,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            role: str
    ):
        self.org_id = org_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = _hash_password(password)
        self.role = role

    def can(self, operation: str, resource: str) -> bool:
        """ Checks if user can perform {operation} on {resource} with their {role} """
        return RoleController.role_can(self.role, operation, resource)

    def check_password(self, password: str) -> bool:
        """ Checks the provided password against the stored password """
        salt = self.password[:64]
        stored_password = self.password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512',
                                      password.encode('utf-8'),
                                      salt.encode('ascii'),
                                      100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == stored_password

    def claims(self) -> dict:
        """ Returns claims for JWT """
        return {
            "aud": self.jwt_aud(),
            "claims": {
                "role": self.role,
                "org": self.org_id,
                "username": self.username
            }
        }

    def jwt_aud(self) -> str:
        return _get_jwt_aud(self.org_id)

    def jwt_secret(self) -> str:
        return _get_jwt_secret(self.org_id)

    def log(self, operation: str, resource: str) -> None:
        """ Logs the {operation} on {resource} from this {user} """
        from app.Controllers.LogControllers import RBACAuditLogController
        RBACAuditLogController.log(self, operation, resource)

    def as_dict(self) -> dict:
        """ Returns dict repr of User """
        return {
            "org_id": self.org_id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "jwt_aud": self.jwt_aud,
            "jwt_secret": self.jwt_secret
        }
