import binascii
import datetime
import hashlib
import os
import typing
from app import DBBase
from app.Controllers.RBAC.RoleController import RoleController
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship


def _hash_password(password: str) -> str:
    """
    Hash a password for storing. See https://www.vitoshacademy.com/hashing-passwords-in-python/
    A random salt is created with a length of 60 bytes.
    The password is then hashed 100,000 times.
    The salt is prepended to the hashed password.

    :param password: The password to hash.

    :return: The password hashed.
    """
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def _get_jwt_secret(org_id: int) -> str:
    """
    Gets the JWT secret for this users organisation
    :param org_id:  The id of the user's organisation
    :return:        The JWT secret.
    """
    from app.Controllers import OrganisationController
    user_org = OrganisationController.get_org_by_id(org_id)
    return user_org.jwt_secret


def _get_jwt_aud(org_id: int) -> str:
    """
    Gets the JWT aud for this users organisation. The aud (audience claim) is unique per
    organisation, and identifies the org.
    :param org_id: The org's id
    :return: The aud claim
    """
    from app.Controllers import OrganisationController
    user_org = OrganisationController.get_org_by_id(org_id)
    return user_org.jwt_aud


class User(DBBase):
    __tablename__ = "users"

    id = Column('id', Integer(), primary_key=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    email = Column('email', String())
    first_name = Column('first_name', String())
    last_name = Column('last_name', String())
    password = Column('password', String())
    job_title = Column('job_title', String())
    role = Column('role', String(), ForeignKey('rbac_roles.id'))
    failed_login_attempts = Column('failed_login_attempts', Integer(), default=0)
    failed_login_time = Column('failed_login_time', DateTime, default=None)
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    orgs = relationship("Organisation")
    roles = relationship("Role")

    def __init__(
            self,
            org_id: int,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            job_title: str,
            role: str
    ):
        self.org_id = org_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = _hash_password(password)
        self.job_title = job_title
        self.role = role

    def can(self, operation: str, resource: str) -> typing.Union[bool, str]:
        """
        Checks if user can perform {operation} on {resource} with their {role}. Basically checks
        if their role can do this.
        :param operation:   The operation to perform.
        :param resource:    The affected resource.
        :return:            True if they can do the thing, or False.
        """
        return RoleController.role_can(self.role, operation, resource)

    def check_password(self, password: str) -> bool:
        """
        Checks the provided password against the stored password. Hash the password like when
        it's stored and then compare.
        :param password:    The password to check.
        :return:            True if it matches or False.
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
                "user_id": self.id
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

    def log(self, **kwargs) -> None:
        """
        Logs an action that a user would perform.
        :param kwargs:  operation, resource, optional(resource_id)
        """
        from app.Controllers.LogControllers import RBACAuditLogController
        RBACAuditLogController.log(self, **kwargs)

    def reset_password(self, password) -> None:
        """
        Resets the user's password
        :param password: The password
        :return: None
        """
        self.password = _hash_password(password)

    def is_active(self) -> None:
        """
        Marks the user as active
        :return:
        """
        from app.Controllers import ActiveUserController
        ActiveUserController.user_is_active(self)

    def is_inactive(self) -> None:
        """
        Marks the user as inactive
        :return:
        """
        from app.Controllers import ActiveUserController
        ActiveUserController.user_is_inactive(self)

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a User object
        """
        return {
            "id": self.id,
            "org_id": self.org_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "job_title": self.job_title
        }
