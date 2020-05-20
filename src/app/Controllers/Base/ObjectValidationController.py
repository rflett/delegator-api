import datetime
import typing
import uuid

import jwt
from flask_restx import Resource
from flask import current_app
from sqlalchemy import exists, and_, func

from app.Extensions.Database import session_scope
from app.Extensions.Errors import AuthorizationError, ValidationError, ResourceNotFoundError
from app.Models.Dao import User, TaskTemplate, Task, TaskLabel, UserPasswordToken
from app.Models.RBAC import Role
from app.Services import UserService

user_service = UserService()


class ObjectValidationController(Resource):
    @staticmethod
    def create_service_account_jwt() -> str:
        """Create a JWT token to make requests to other services"""
        token = jwt.encode(
            payload={
                "claims": {"type": "service-account", "service-account-name": "delegator-api"},
                "jti": str(uuid.uuid4()),
                "aud": "delegator.com.au",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=30),
            },
            key=current_app.config["JWT_SECRET"],
            algorithm="HS256",
        ).decode("utf-8")
        return "Bearer " + token

    @staticmethod
    def check_auth_scope(affected_user: User, **kwargs):
        """Compares a users scope against the action they're trying to do"""
        if affected_user is not None:
            if kwargs["auth_scope"] == "SELF" and kwargs["req_user"].id != affected_user.id:
                raise AuthorizationError(f"User {kwargs['req_user'].id} can only perform this action on themselves.")
            elif kwargs["auth_scope"] == "ORG" and kwargs["req_user"].org_id != affected_user.org_id:
                raise AuthorizationError(
                    f"User {kwargs['req_user'].id} can only perform this action within their organisation."
                )

    @staticmethod
    def check_password_reqs(password: str) -> bool:
        """Ensures a password meets minimum security requirements."""
        min_length = 6
        min_special_chars = 1
        min_caps = 1
        special_chars = r" !#$%&\'()*+,-./:;<=>?@[\]^_`{|}~"
        if len(password) < min_length:
            raise ValidationError(f"Password length less than {min_length}.")
        if len([char for char in password if char in special_chars]) < min_special_chars:
            raise ValidationError(f"Password requires more than {min_special_chars} special character(s).")
        if sum(1 for c in password if c.isupper()) < min_caps:
            raise ValidationError(f"Password requires more than {min_caps} capital letter(s).")
        return True

    def check_task_assignee(self, assignee: typing.Optional[int], **kwargs) -> typing.Union[int, None]:
        """Check if the user has permissions to assign this person to a task."""
        if assignee is not None:
            user = self.check_user_id(assignee, should_exist=True)
            self.check_auth_scope(user, **kwargs)
            return user.id
        else:
            return None

    @staticmethod
    def check_task_id(task_id: int, org_id: int) -> Task:
        """Check that the task exist and return it if it does."""
        with session_scope() as session:
            # filter with the org so that's scoped to the requesting user
            task = session.query(Task).filter_by(id=task_id, org_id=org_id).first()

        if task is None:
            raise ResourceNotFoundError(f"Task {task_id} doesn't exist")
        else:
            return task

    @staticmethod
    def check_task_template_id(template_id: int):
        """Check if a task type exists."""
        if template_id is None:
            return
        with session_scope() as session:
            if not session.query(exists().where(TaskTemplate.id == template_id)).scalar():
                raise ResourceNotFoundError("Task template doesn't exist")

    @staticmethod
    def check_task_labels(labels: typing.List[int], org_id: int) -> None:
        """Check to make sure that the labels are valid"""
        with session_scope() as session:
            for label_id in labels:
                if not session.query(
                    exists().where(and_(TaskLabel.id == label_id, TaskLabel.org_id == org_id))
                ).scalar():
                    raise ResourceNotFoundError(f"Label {label_id} doesn't exist")

    @staticmethod
    def check_user_id(
        identifier: typing.Union[str, int], should_exist: typing.Optional[bool] = None
    ) -> typing.Union[None, User, str]:
        """Given a users email or ID, check whether it should or shouldn't exist"""
        # optionally check if it exists or not
        if should_exist is not None:

            with session_scope() as session:
                if isinstance(identifier, str):
                    user = session.query(User).filter(func.lower(User.email) == func.lower(identifier)).first()
                else:
                    user = session.query(User).filter_by(id=identifier).first()

            if should_exist and user is None:
                raise ResourceNotFoundError("User doesn't exist")
            elif not should_exist and user is not None:
                raise ValidationError("User already exists")
            elif not should_exist and user is None:
                # return the email
                return identifier

            return user

    @staticmethod
    def check_user_role(req_user: User, role: str, user_to_update: User = None) -> str:
        """Given a users role, check that it exist and that the user can pass the role on to the recipient."""
        with session_scope() as session:
            _role = session.query(Role).filter_by(id=role).first()
        if _role is None:
            raise ResourceNotFoundError(f"Role {role} doesn't exist")
        elif _role.rank < req_user.roles.rank:
            raise AuthorizationError(f"No permissions to pass the role {role} on")
        elif user_to_update is None:
            return _role.id
        elif user_to_update is not None and user_to_update.roles.rank < req_user.roles.rank:
            raise AuthorizationError(f"No permissions to pass the role {role} on")
        elif user_to_update.role != role and user_service.is_user_only_org_admin(user_to_update):
            raise ValidationError("Can't demote the only remaining Administrator's role")
        else:
            return _role.id

    @staticmethod
    def validate_password_token(token: str) -> UserPasswordToken:
        """Validates the create first time password link"""
        with session_scope() as session:
            password_token = session.query(UserPasswordToken).filter_by(token=token).first()

        if password_token is None:
            raise ValidationError("Invite token does not exist or has expired.")
        else:
            return password_token

    @staticmethod
    def purge_expired_tokens() -> None:
        """Removes password tokens that have expired."""
        with session_scope() as session:
            now = int(datetime.datetime.utcnow().timestamp())
            delete_expired = (
                session.query(UserPasswordToken)
                .filter((UserPasswordToken.expire_after + UserPasswordToken.created_at) < now)
                .delete()
            )
            if delete_expired > 0:
                current_app.logger.info(f"Purged {delete_expired} password tokens which expired.")
