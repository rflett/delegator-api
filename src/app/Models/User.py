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
    """ 
    Hash a password for storing. See https://www.vitoshacademy.com/hashing-passwords-in-python/
    A random salt is created with a length of 60 bytes. 
    The password is then hashed 100,000 times.
    The salt is prepended to the hashed password.
    
    :param password str: The password to hash.

    :return: The password hashed.
    """
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def _get_jwt_secret(org_id: int) -> str:
    """ 
    Gets the JWT secret for this users organisation 
    
    :param org_id int: The id of the user's organisation

    :return: The JWT secret.
    """
    from app.Controllers import OrganisationController
    user_org = OrganisationController.get_org_by_id(org_id)
    return user_org.jwt_secret


def _get_jwt_aud(org_id: int) -> str:
    """ 
    Gets the JWT aud for this users organisation. The aud (audience claim) is unique per
    organisation, and identifies the org.

    :param org_id int: The org's id

    :return: The aud claim
    """
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
        """ 
        Checks if user can perform {operation} on {resource} with their {role}. Basically checks
        if their role can do this.
        
        :param operation str:   The operation to perform.
        :param resource str:    The affected resource.

        :return: True if they can do the thing, or False.
        """
        return RoleController.role_can(self.role, operation, resource)

    def check_password(self, password: str) -> bool:
        """ 
        Checks the provided password against the stored password. Hash the password like when
        it's stored and then compare.
        
        :param password str: The password to check.

        :return: True if it matches or False.
        """
        salt = self.password[:64]
        stored_password = self.password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512',
                                      password.encode('utf-8'),
                                      salt.encode('ascii'),
                                      100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == stored_password

    def claims(self) -> dict:
        """
        Get the claims for a user. The claims make up part of the JWT token payload.

        :return: A dict of claims.
        """
        return {
            "aud": self.jwt_aud(),
            "claims": {
                "role": self.role,
                "org": self.org_id,
                "username": self.username
            }
        }

    def jwt_aud(self) -> str:
        """
        Get's the users JWT aud.

        :return: JWT aud
        """
        return _get_jwt_aud(self.org_id)

    def jwt_secret(self) -> str:
        """
        Get's the users JWT secret.

        :return: JWT secret
        """
        return _get_jwt_secret(self.org_id)

    def log(self, operation: str, resource: str) -> None:
        """ 
        Logs the {operation} on {resource} from this {user} 
        
        :param operation str:   The operation that was performed.
        :param resource str:    The resource that was affected.
        """
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
