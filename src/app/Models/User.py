import _thread
import binascii
import datetime
import hashlib
import os
import random
import string
import typing
from os import getenv

from boto3.dynamodb.conditions import Key
from sqlalchemy import exists

from app import db, session_scope, logger, user_activity_table, app, subscription_api
from app.Models import FailedLogin, Task, UserSetting
from app.Models.RBAC import Log, Permission
from app.Models.LocalMockData import MockActivity


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
    role_before_locked = db.Column('role_before_locked', db.String, db.ForeignKey('rbac_roles.id'), default=None)
    disabled = db.Column('disabled', db.DateTime, default=None)
    deleted = db.Column('deleted', db.DateTime, default=None)
    failed_login_attempts = db.Column('failed_login_attempts', db.Integer, default=0)
    failed_login_time = db.Column('failed_login_time', db.DateTime, default=None)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)
    created_by = db.Column('created_by', db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column('updated_at', db.DateTime, default=datetime.datetime.utcnow)
    updated_by = db.Column('updated_by', db.Integer, db.ForeignKey('users.id'))
    password_last_changed = db.Column('password_last_changed', db.DateTime, default=datetime.datetime.utcnow)

    orgs = db.relationship("Organisation", backref="users")
    roles = db.relationship("Role", backref="rbac_roles", foreign_keys=[role])
    created_bys = db.relationship("User", foreign_keys=[created_by])
    updated_bys = db.relationship("User", foreign_keys=[updated_by])

    def __init__(
            self,
            org_id: int,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            job_title: str,
            role: str,
            role_before_locked: str = None,
            created_by: typing.Union[int, None] = None,
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
        self.role_before_locked = role_before_locked
        self.created_by = created_by
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
            permission = session.query(Permission).filter_by(
                role_id=self.role,
                operation_id=operation,
                resource_id=resource
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
            "aud": self.orgs.jwt_aud,
            "claims": {
                "role": self.role,
                "org": self.org_id,
                "user_id": self.id
            }
        }

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
                    f"a resource_id of {resource_id}")

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
                session.query(FailedLogin).filter_by(email=self.email).delete()

            logger.info(f"cleared failed logins for {self.email}")

    def delete(self, req_user) -> None:
        """ Deletes the user """
        def make_random() -> str:
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))

        self.email = f"{make_random()}@{make_random()}.com"
        self.password = _hash_password(make_random())
        self.deleted = datetime.datetime.utcnow()

        subscription_api.decrement_plan_quantity(self.orgs.chargebee_subscription_id)

        # drop their tasks
        with session_scope() as session:
            users_tasks = session.query(Task).filter_by(assignee=self.id).all()
        for task in users_tasks:
            task.drop(req_user)

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a User object
        """
        if self.disabled is None:
            disabled = None
        else:
            disabled = self.disabled.strftime(app.config['RESPONSE_DATE_FORMAT'])

        if self.deleted is None:
            deleted = None
        else:
            deleted = self.deleted.strftime(app.config['RESPONSE_DATE_FORMAT'])

        return {
            "id": self.id,
            "org_id": self.org_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "role_before_locked": self.role_before_locked,
            "disabled": disabled,
            "job_title": self.job_title,
            "deleted": deleted,
            "created_at": self.created_at.strftime(app.config['RESPONSE_DATE_FORMAT']),
            "created_by": self.created_by,
            "updated_at": self.updated_at.strftime(app.config['RESPONSE_DATE_FORMAT']),
            "updated_by": self.updated_by
        }

    def fat_dict(self) -> dict:
        """ Returns a full user dict with all of its FK's joined. """
        from app.Controllers import SettingsController

        with session_scope() as session:
            created_by = session.query(User).filter_by(id=self.created_by).first()
            updated_by = session.query(User).filter_by(id=self.updated_by).first()

        user_dict = self.as_dict()
        user_dict['role'] = self.roles.as_dict()
        user_dict['created_by'] = created_by.name()
        user_dict['updated_by'] = updated_by.name() if updated_by is not None else None
        user_dict['settings'] = SettingsController.get_user_settings(self.id).as_dict()

        return user_dict

    def activity(self) -> list:
        """ Returns the activity of a user"""
        if getenv('APP_ENV', 'Local') == 'Local':
            activity = MockActivity()
            return activity.data

        activity = user_activity_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('id').eq(self.id)
        )
        logger.info(f"Found {activity.get('Count')} activity items for user id {self.id}")

        log = []

        for item in activity.get('Items'):
            try:
                del item['id']
                activity_timestamp_date = datetime.datetime.strptime(item['activity_timestamp'], "%Y%m%dT%H%M%S.%fZ")
                item['activity_timestamp'] = activity_timestamp_date.strftime(app.config['RESPONSE_DATE_FORMAT'])
                log.append(item)
            except KeyError:
                logger.error(f"Key 'id' was missing from activity item. Table:{user_activity_table.name} Item:{item}")

        return log

    def name(self) -> str:
        """ Returns their full name """
        return self.first_name + " " + self.last_name

    def create_settings(self) -> None:
        """ Creates the settings for this user """
        from app.Controllers.SettingsController import SettingsController
        SettingsController.set_user_settings(UserSetting(self.id))
