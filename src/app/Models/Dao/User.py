import binascii
import datetime
import hashlib
import os
import pytz
import typing
import uuid
from os import getenv

import boto3
import structlog
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from flask import current_app
from sqlalchemy import exists, func

from app.Extensions.Database import db, session_scope
from app.Extensions.Errors import AuthorizationError
from app.Models.Dao import ActiveUser
from app.Models.RBAC import Log, Permission
from app.Models.Enums import Roles
from app.Models.LocalMockData import MockActivity


dyn_db = boto3.resource("dynamodb")
s3 = boto3.client("s3")
cloudfront = boto3.client("cloudfront")
log = structlog.getLogger()


def _hash_password(password: str) -> str:
    """
    Hash a password for storing. See https://www.vitoshacademy.com/hashing-passwords-in-python/
    A random salt is created with a length of 60 bytes.
    The password is then hashed 100,000 times.
    The salt is prepended to the hashed password.

    :param password: The password to hash.

    :return: The password hashed.
    """
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode("ascii")
    pwdhash = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 1000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode("ascii")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column("id", db.Integer, primary_key=True)
    uuid = db.Column("uuid", db.String)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    email = db.Column("email", db.String)
    previous_email = db.Column("previous_email", db.String, default=None)
    first_name = db.Column("first_name", db.String)
    last_name = db.Column("last_name", db.String)
    password = db.Column("password", db.String, default=None)
    job_title = db.Column("job_title", db.String, default=None)
    role = db.Column("role", db.String, db.ForeignKey("rbac_roles.id"))
    role_before_locked = db.Column("role_before_locked", db.String, db.ForeignKey("rbac_roles.id"), default=None)
    disabled = db.Column("disabled", db.DateTime, default=None)
    deleted = db.Column("deleted", db.DateTime, default=None)
    failed_login_attempts = db.Column("failed_login_attempts", db.Integer, default=0)
    failed_login_time = db.Column("failed_login_time", db.DateTime, default=None)
    created_at = db.Column("created_at", db.DateTime, default=datetime.datetime.utcnow)
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column("updated_at", db.DateTime, default=datetime.datetime.utcnow)
    updated_by = db.Column("updated_by", db.Integer, db.ForeignKey("users.id"))
    password_last_changed = db.Column("password_last_changed", db.DateTime, default=datetime.datetime.utcnow)

    orgs = db.relationship("Organisation", backref="users")
    roles = db.relationship("Role", backref="rbac_roles", foreign_keys=[role])
    updated_bys = db.relationship("User", foreign_keys=[updated_by])

    def __init__(
        self,
        org_id: int,
        email: str,
        first_name: str,
        last_name: str,
        role: str,
        job_title: str = None,
        password: str = None,
        role_before_locked: str = None,
        created_by: typing.Union[int, None] = None,
        disabled: typing.Union[datetime.datetime, None] = None,
        deleted: typing.Union[datetime.datetime, None] = None,
    ):
        self.uuid = str(uuid.uuid4())
        self.org_id = org_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = _hash_password(password) if password is not None else None
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
            permission = (
                session.query(Permission)
                .filter_by(role_id=self.role, operation_id=operation, resource_id=resource)
                .first()
            )

        if permission is None:
            raise AuthorizationError(f"No permissions to {operation} {resource}.")
        else:
            return permission.resource_scope

    def password_correct(self, password: str) -> bool:
        """
        Checks the provided password against the stored password. Hash the password like when
        it's stored and then compare.
        :param password:    The password to check.
        :return:            True if it matches or False.
        """
        if self.password is None:
            return False
        salt = self.password[:64]
        stored_password = self.password[64:]
        pwdhash = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt.encode("ascii"), 1000)
        pwdhash = binascii.hexlify(pwdhash).decode("ascii")
        return pwdhash == stored_password

    def claims(self) -> dict:
        """
        Get the claims for a user. The claims make up part of the JWT token payload.
        :return: A dict of claims.
        """
        return {
            "aud": "delegator.com.au",
            "claims": {"role": self.role, "org": self.org_id, "user-id": self.id, "type": "user", "email": self.email},
        }

    def log(self, operation: str, resource: str, resource_id: typing.Union[int, None] = None) -> None:
        """
        Logs an action that a user would perform.
        """
        audit_log = Log(
            org_id=self.org_id, user_id=self.id, operation=operation, resource=resource, resource_id=resource_id
        )
        with session_scope() as session:
            session.add(audit_log)
        log.info(f"user with id {self.id} did {operation} on {resource} with " f"a resource_id of {resource_id}")

    def set_password(self, password) -> None:
        """
        Sets the user's password
        :param password: The password
        :return: None
        """
        self.password = _hash_password(password)

    def is_active(self) -> None:
        """Marks user as active if they are not active already. If they're already active then update them."""
        with session_scope() as session:
            already_active = session.query(ActiveUser).filter_by(user_id=self.id).first()
            if already_active is None:
                # user is not active, so create
                active_user = ActiveUser(
                    user_id=self.id,
                    org_id=self.org_id,
                    first_name=self.first_name,
                    last_name=self.last_name,
                    last_active=datetime.datetime.utcnow(),
                )
                session.add(active_user)
            else:
                # user is active, so update
                already_active.last_active = datetime.datetime.utcnow()

    def is_inactive(self) -> None:
        """Mark user as inactive by deleting their record in the active users table"""
        with session_scope() as session:
            session.query(ActiveUser).filter_by(user_id=self.id).delete()

    def last_active(self) -> typing.Union[str, None]:
        """Returns when the user was last active"""
        with session_scope() as session:
            qry = session.query(ActiveUser).filter_by(user_id=self.id).first()
            if qry is None:
                return None
            else:
                last_active = pytz.utc.localize(qry.last_active)
                return last_active.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

    def clear_failed_logins(self) -> None:
        """ Clears a user's failed login attempts """
        from app.Models.Dao import FailedLogin

        with session_scope() as session:
            failed_email = session.query(exists().where(FailedLogin.email == self.email)).scalar()

            if failed_email:
                session.query(FailedLogin).filter_by(email=self.email).delete()

            log.info(f"cleared failed logins for {self.email}")

    def delete(self, req_user) -> None:
        """ Deletes the user """
        from app.Models.Dao import Task
        from app.Models import Subscription

        if self.disabled is None:
            subscription = Subscription(self.orgs.chargebee_subscription_id)
            subscription.decrement_subscription(req_user)

        # drop their tasks
        with session_scope() as session:
            users_tasks = session.query(Task).filter_by(assignee=self.id).all()

        for task in users_tasks:
            task.drop(req_user)

        # delete their avatar
        self.previous_email = self.email
        self.email = None
        self.password = None
        self.deleted = datetime.datetime.utcnow()
        self._delete_avatar()

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a User object
        """
        if self.disabled is None:
            disabled = None
        else:
            disabled = pytz.utc.localize(self.disabled)
            disabled = disabled.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.deleted is None:
            deleted = None
        else:
            deleted = pytz.utc.localize(self.deleted)
            deleted = deleted.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        created_at = pytz.utc.localize(self.created_at)
        updated_at = pytz.utc.localize(self.updated_at)

        return {
            "id": self.id,
            "uuid": self.uuid,
            "org_id": self.org_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "role_before_locked": self.role_before_locked,
            "disabled": disabled,
            "job_title": self.job_title,
            "deleted": deleted,
            "created_at": created_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"]),
            "created_by": self.created_by,
            "updated_at": updated_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"]),
            "updated_by": self.updated_by,
            "invite_accepted": self.invite_accepted(),
            "invite_expires_in": None if self.invite_accepted() else self.invite_expires_in(),
            "last_seen": self.last_active(),
        }

    def fat_dict(self) -> dict:
        """ Returns a full user dict with all of its FK's joined. """
        with session_scope() as session:
            created_by = session.query(User.first_name, User.last_name).filter_by(id=self.created_by).first()
            updated_by = session.query(User.first_name, User.last_name).filter_by(id=self.updated_by).first()

        user_dict = self.as_dict()
        user_dict["role"] = self.roles.as_dict()
        user_dict["created_by"] = created_by[0] + " " + created_by[1]
        user_dict["updated_by"] = updated_by[0] + " " + updated_by[1] if updated_by is not None else None

        return user_dict

    def activity(self) -> list:
        """ Returns the activity of a user"""
        if getenv("MOCK_AWS"):
            activity = MockActivity()
            return activity.data

        user_activity_table = dyn_db.Table(current_app.config["USER_ACTIVITY_TABLE"])

        activity = user_activity_table.query(
            Select="ALL_ATTRIBUTES", KeyConditionExpression=Key("id").eq(self.id), ScanIndexForward=False
        )
        log.info(f"Found {activity.get('Count')} activity items for user id {self.id}")

        activity_log = []

        for item in activity.get("Items"):
            activity_timestamp = datetime.datetime.strptime(
                item["activity_timestamp"], current_app.config["DYN_DB_ACTIVITY_DATE_FORMAT"]
            )
            activity_timestamp = pytz.utc.localize(activity_timestamp)
            item["activity_timestamp"] = activity_timestamp.strftime(current_app.config["RESPONSE_DATE_FORMAT"])
            activity_log.append(item)

        return activity_log

    def name(self) -> str:
        """ Returns their full name """
        return self.first_name + " " + self.last_name

    def create_settings(self) -> None:
        """ Creates the settings for this user """
        from app.Models import UserSetting

        setting = UserSetting(self.id)
        setting.update()

    def generate_new_invite(self):
        """Create a new invite token"""
        from app.Models.Dao import UserPasswordToken

        with session_scope() as session:
            # delete old link if there's one
            session.query(UserPasswordToken).filter_by(user_id=self.id).delete()
            # create new link
            token = UserPasswordToken(self.id)
            session.add(token)
        return token

    def invite_accepted(self) -> bool:
        """Check to see if they have accepted their invite"""
        return self.password is not None

    def invite_expires_in(self) -> typing.Union[int, None]:
        """Return when their invite expires"""
        token = self.get_password_token()
        if token is None:
            return

        minutes = int(token.created_at + token.expire_after - datetime.datetime.utcnow().timestamp()) // 60
        if minutes < 0:
            return

        return minutes

    def get_password_token(self):
        """Get the password token if it exists"""
        from app.Models.Dao import UserPasswordToken

        with session_scope() as session:
            token = session.query(UserPasswordToken).filter_by(user_id=self.id).first()

        return token

    def set_avatar(self, file: typing.IO) -> None:
        """Sets the avatar for the user"""
        new_uuid = str(uuid.uuid4())

        try:
            s3.upload_fileobj(
                file,
                current_app.config["ASSETS_BUCKET"],
                f"user/avatar/{new_uuid}.jpg",
                ExtraArgs={"Metadata": {"Content-Type": "image/jpeg"}},
            )
            log.info(f"Uploaded avatar {self.uuid}.jpg")

            self._delete_avatar()

            with session_scope():
                self.uuid = new_uuid

        except ClientError as e:
            log.error(f"error uploading profile avatar - {e}")

    def reset_avatar(self) -> None:
        """Copies the default.jpg avatar to the user uuid to 'reset' it"""
        new_uuid = str(uuid.uuid4())

        try:
            s3.copy_object(
                Bucket=current_app.config["ASSETS_BUCKET"],
                CopySource={"Bucket": current_app.config["ASSETS_BUCKET"], "Key": "user/avatar/default.jpg"},
                Key=f"user/avatar/{new_uuid}.jpg",
            )
            log.info(f"Reset avatar {new_uuid}.jpg")

            self._delete_avatar()

            with session_scope():
                self.uuid = new_uuid

        except ClientError as e:
            log.error(f"Error resetting user avatar - {e}")

    def _delete_avatar(self):
        """Tag avatar for deletion"""
        bucket = current_app.config["ASSETS_BUCKET"]
        key = f"user/avatar/{self.uuid}.jpg"
        try:
            s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet": [{"Key": "deleted", "Value": "true"}]})
            log.info(f"Tagged {bucket}/{key} for deletion")
        except s3.exceptions.NoSuchKey:
            return
        except ClientError as e:
            log.error(f"Error tagging file {bucket}/{key} for deletion - {e}")

    def is_only_org_admin(self) -> bool:
        """Checks to see if the user is the only ORG_ADMIN"""
        if self.role != Roles.ORG_ADMIN:
            return False

        with session_scope() as session:
            org_admins_cnt = (
                session.query(func.count(User.id))
                .filter(
                    User.role == Roles.ORG_ADMIN,
                    User.org_id == self.org_id,
                    User.disabled == None,  # noqa
                    User.deleted == None,  # noqa
                )
                .scalar()
            )

        return True if org_admins_cnt == 1 else False
