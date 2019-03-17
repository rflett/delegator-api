import binascii
import datetime
import hashlib
import os
import typing
from app import db
from app.Controllers.RBAC.RoleController import RoleController


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


class User(db.Model):
    __tablename__ = "users"

    id = db.Column('id', db.Integer, primary_key=True)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    email = db.Column('email', db.String)
    first_name = db.Column('first_name', db.String)
    last_name = db.Column('last_name', db.String)
    password = db.Column('password', db.String)
    job_title = db.Column('job_title', db.String)
    role = db.Column('role', db.String, db.ForeignKey('rbac_roles.id'))
    disabled = db.Column('disabled', db.Boolean, default=False)
    deleted = db.Column('deleted', db.Boolean, default=False)
    failed_login_attempts = db.Column('failed_login_attempts', db.Integer, default=0)
    failed_login_time = db.Column('failed_login_time', db.DateTime, default=None)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)

    orgs = db.relationship("Organisation")
    roles = db.relationship("Role")

    def __init__(
            self,
            org_id: int,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            job_title: str,
            role: str,
            disabled: bool = False,
            deleted: bool = False
    ):
        self.org_id = org_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = _hash_password(password)
        self.job_title = job_title
        self.role = role
        self.disabled = disabled
        self.deleted = deleted

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
            "disabled": self.disabled,
            "job_title": self.job_title,
            "deleted": self.deleted
        }
