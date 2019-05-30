import _thread
import binascii
import datetime
import hashlib
import os
import random
import string
import typing
from app import db, session_scope, logger, user_activity_table
from app.Models import FailedLogin, Organisation
from app.Models.RBAC import Role, Log, Permission
from boto3.dynamodb.conditions import Key
from sqlalchemy import exists


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
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 1000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


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
    disabled = db.Column('disabled', db.DateTime, default=None)
    deleted = db.Column('deleted', db.DateTime, default=None)
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
            disabled: typing.Union[datetime.datetime, None] = None,
            deleted: typing.Union[datetime.datetime, None] = None
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
        Checks if user can perform {operation} on {resource} with their {role}.
        :param operation:   The operation to perform.
        :param resource:    The affected resource.
        :return:            True if they can do the thing, or False.
        """
        with session_scope() as session:
            permission = session.query(Permission).filter(
                Permission.role_id == self.role,
                Permission.operation_id == operation,
                Permission.resource_id == resource
            ).first()

        if permission is None:
            logger.info(f"permission with role:{self.role}, operation:{operation}, resource:{resource} does not exist")
            return False
        else:
            return permission.resource_scope

    def password_correct(self, password: str) -> bool:
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
                                      1000)
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
        Gets the JWT aud for this users organisation. The aud (audience claim) is unique per
        organisation, and identifies the org.
        :return: The aud claim
        """
        from app.Controllers import OrganisationController
        user_org = OrganisationController.get_org_by_id(self.org_id)
        return user_org.jwt_aud

    def jwt_secret(self) -> str:
        """
        Gets the JWT secret for this users organisation
        :return:        The JWT secret.
        """
        from app.Controllers import OrganisationController
        user_org = OrganisationController.get_org_by_id(self.org_id)
        return user_org.jwt_secret

    def log(self, operation: str, resource: str, resource_id: typing.Union[int, None] = None) -> None:
        """
        Logs an action that a user would perform.
        """
        audit_log = Log(
            org_id=self.org_id,
            user_id=self.id,
            operation=operation,
            resource=resource,
            resource_id=resource_id
        )
        with session_scope() as session:
            session.add(audit_log)
        logger.info(f"user with id {self.id} did {operation} on {resource} with "
                    f"and id of {resource_id}")

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
        _thread.start_new_thread(ActiveUserController.user_is_active, (self,))

    def is_inactive(self) -> None:
        """
        Marks the user as inactive
        :return:
        """
        from app.Controllers import ActiveUserController
        _thread.start_new_thread(ActiveUserController.user_is_inactive, (self,))

    def clear_failed_logins(self) -> None:
        """ Clears a user's failed login attempts """
        with session_scope() as session:
            failed_email = session.query(exists().where(FailedLogin.email == self.email)).scalar()

            if failed_email:
                session.query(FailedLogin).filter(FailedLogin.email == self.email).delete()

            logger.info(f"cleared failed logins for {self.email}")

    def anonymize(self) -> None:
        """ Removes any PII from the user object """
        def make_random() -> str:
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))

        self.first_name = make_random()
        self.last_name = make_random()
        self.email = f"{make_random()}@{make_random()}.com"
        self.password = _hash_password(make_random())
        self.deleted = datetime.datetime.utcnow()

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a User object
        """
        if self.disabled is None:
            disabled = None
        else:
            disabled = self.disabled.strftime("%Y-%m-%d %H:%M:%S%z")

        if self.deleted is None:
            deleted = None
        else:
            deleted = self.deleted.strftime("%Y-%m-%d %H:%M:%S%z")

        return {
            "id": self.id,
            "org_id": self.org_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "disabled": disabled,
            "job_title": self.job_title,
            "deleted": deleted
        }

    def fat_dict(self) -> dict:
        """ Returns a full user dict with all of its FK's joined. """
        from app.Controllers import SettingsController

        with session_scope() as session:
            user_qry = session.query(User, Role, Organisation) \
                .join(User.roles) \
                .join(User.orgs) \
                .filter(User.id == self.id) \
                .first()

        user, role, org = user_qry
        extras = {}

        # prepend role attrs with role_
        for k, v in role.as_dict().items():
            # key exclusions
            if k not in ['id', 'rank']:
                extras[f'role_{k}'] = v

        # prepend org attrs with org_
        for k, v in org.as_dict().items():
            # key exclusions
            if k not in ['id', 'jwt_aud', 'jwt_secret']:
                extras[f'org_{k}'] = v

        # get settings
        extras['settings'] = SettingsController.get_user_settings(user.id).as_dict()

        # merge role with user, with return dict sorted
        return dict(
                sorted(
                    {
                        **user.as_dict(),
                        **extras
                    }.items()
                )
        )

    def activity(self) -> list:
        """ Returns the activity of a user"""
        activity = user_activity_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('id').eq(self.id)
        )
        logger.info(f"Found {activity.get('Count')} activity items for user id {self.id}")

        log = []

        for item in activity.get('Items'):
            try:
                del item['id']
                log.append(item)
            except KeyError:
                logger.error(f"Key 'id' was missing from activity item. Table:{user_activity_table.name} Item:{item}")

        return log

    def name(self) -> str:
        """ Returns their full name """
        return self.first_name + " " + self.last_name
