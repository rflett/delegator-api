import datetime
import dateutil
import typing

from sqlalchemy import exists, and_, func

from app import logger, app, session_scope
from app.Controllers.Base.ResponseController import ResponseController
from app.Exceptions import AuthorizationError, ValidationError, ResourceNotFoundError
from app.Models import User, TaskType, Task, TaskPriority, TaskStatus, TaskTypeEscalation, TaskLabel, UserPasswordToken
from app.Models.RBAC import Role
from app.Services import UserService

user_service = UserService()


class ObjectValidationController(ResponseController):
    @staticmethod
    def check_auth_scope(affected_user: User, **kwargs):
        """Compares a users scope against the action they're trying to do"""
        if affected_user is not None:
            if kwargs["auth_scope"] == "SELF" and kwargs["req_user"].id != affected_user.id:
                raise AuthorizationError(f"User {kwargs['req_user'].id} can only perform this action on themselves.")
            elif kwargs["auth_scope"] == "ORG" and kwargs["req_user"].org_id != affected_user.org_id:
                raise AuthorizationError(
                    f"User {kwargs['req_user'].id} can only perform this" f" action within their organisation."
                )

    @staticmethod
    def check_escalation(task_type_id: int, display_order: int, should_exist: bool) -> None:
        """Check if a task escalation should exist or not"""
        with session_scope() as session:
            escalation_exists = session.query(
                exists().where(
                    and_(
                        TaskTypeEscalation.task_type_id == task_type_id,
                        TaskTypeEscalation.display_order == display_order,
                    )
                )
            ).scalar()
            if should_exist and not escalation_exists:
                raise ResourceNotFoundError(f"Task type escalation {task_type_id}:{display_order} doesn't exist")
            elif not should_exist and escalation_exists:
                raise ValidationError(f"Task type escalation {task_type_id}:{display_order} already exists.")

    @staticmethod
    def check_int(param: int, param_name: str, allow_negative: bool = False) -> int:
        """Ensures the param is an int and is positive
        In python bools are ints, so we need to checks that it's a bool before we check that it's an int"""
        if isinstance(param, bool):
            raise ValidationError(f"Bad {param_name}, expected int got {type(param)}.")
        if not isinstance(param, int):
            raise ValidationError(f"Bad {param_name}, expected int got {type(param)}.")
        if not allow_negative and param < 0:
            raise ValidationError(f"{param_name} is negative.")
        return param

    def check_optional_int(self, param: int, param_name: str, allow_negative: bool = False) -> typing.Union[int, None]:
        """If the param is not None, check that its a valid str."""
        if param is not None:
            return self.check_int(param, param_name, allow_negative=allow_negative)
        else:
            return param

    @staticmethod
    def check_optional_str(param: str, param_name: str) -> typing.Union[str, None]:
        """If the param is not None, check that its a valid str."""
        if param is not None:
            if not isinstance(param, str):
                raise ValidationError(f"Bad {param_name}, expected str got {type(param)}.")
            return param.strip()
        else:
            return param

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

    @staticmethod
    def check_str(param: str, param_name: str) -> str:
        """Checks that the param is a str, has more than 0 chars in it, and returns the stripped str."""
        if not isinstance(param, str):
            raise ValidationError(f"Bad {param_name}, expected str got {type(param)}.")
        if len(param.strip()) == 0:
            raise ValidationError(f"{param_name} is required.")
        return param.strip()

    @staticmethod
    def check_optional_date(date_str: typing.Optional[str], param_name: str) -> typing.Union[None, datetime.datetime]:
        """Verify a date can be converted to a datetime and is not in the past"""
        if date_str is not None:
            try:
                date_parsed = dateutil.parser.parse(date_str)
                if date_parsed < datetime.datetime.now(datetime.timezone.utc):
                    raise ValidationError(f"{param_name} is in the past.")
                return date_parsed
            except ValueError as e:
                logger.error(str(e))
                raise ValidationError(f"Could not parse {param_name} {date_str} to date.")
        return None

    def check_task_assignee(self, assignee: typing.Optional[int], **kwargs) -> typing.Union[int, None]:
        """Check if the user has permissions to assign this person to a task."""
        if assignee is not None:
            user = self.check_user_id(assignee, should_exist=True)
            self.check_auth_scope(user, **kwargs)
            return user.id
        else:
            return None

    def check_task_id(self, task_id: int, org_id: int) -> Task:
        """Check that the task exist and return it if it does."""
        task_id = self.check_int(task_id, "id")  # the request uses 'id'

        with session_scope() as session:
            task = session.query(Task).filter_by(id=task_id, org_id=org_id).first()

        if task is None:
            raise ResourceNotFoundError(f"Task {task_id} doesn't exist")
        else:
            return task

    def check_task_priority(self, priority: typing.Union[int, None]) -> typing.Union[int, None]:
        """Check that a task priority exists."""
        priority = self.check_int(priority, "task_priority")

        with session_scope() as session:
            if not session.query(exists().where(TaskPriority.priority == priority)).scalar():
                raise ResourceNotFoundError(f"Priority {priority} doesn't exist")

        return priority

    def check_task_status(self, task_status: str) -> str:
        """Check that a task status exists."""
        task_status = self.check_str(task_status, "task_status")

        with session_scope() as session:
            if not session.query(exists().where(TaskStatus.status == task_status)).scalar():
                raise ResourceNotFoundError(f"Task status {task_status} doesn't exist")

        return task_status.strip()

    def check_task_type_id(self, task_type_id: int) -> int:
        """Check if a task type exists."""
        task_type_id = self.check_int(task_type_id, "task_type_id")

        with session_scope() as session:
            if not session.query(exists().where(TaskType.id == task_type_id)).scalar():
                raise ResourceNotFoundError(f"Task type {task_type_id} doesn't exist")

        return task_type_id

    def check_task_labels(self, labels: typing.List[int], org_id: int) -> typing.List[int]:
        """Check to make sure that the labels are valid"""
        if len(labels) > 3:
            raise ValidationError(f"Tasks can only have up to 3 labels, you've supplied {len(labels)}.")
        with session_scope() as session:
            for label_id in labels:
                self.check_int(label_id, "label id")
                if not session.query(
                    exists().where(and_(TaskLabel.id == label_id, TaskLabel.org_id == org_id))
                ).scalar():
                    raise ResourceNotFoundError(f"Label {label_id} doesn't exist")
        return labels

    @staticmethod
    def check_user_disabled(disabled: typing.Optional[datetime.datetime]) -> typing.Union[None, datetime.datetime]:
        """Verify that the user disabled field can be converted to a datetime."""
        if disabled is not None:
            try:
                disabled = datetime.datetime.strptime(disabled, app.config["REQUEST_DATE_FORMAT"])
                return disabled
            except ValueError:
                raise ValidationError(
                    f"Couldn't convert disabled {disabled} to datetime.datetime, please ensure it is "
                    f"in the format {app.config['REQUEST_DATE_FORMAT']}"
                )

    @staticmethod
    def check_user_id(
        identifier: typing.Union[str, int], should_exist: typing.Optional[bool] = None
    ) -> typing.Union[None, User, str]:
        """Given a users email or ID, check whether it should or shouldn't exist"""
        # validate the identifier
        if isinstance(identifier, bool):
            raise ValidationError(f"Bad user_id, expected int|str got {type(identifier)}.")
        if not isinstance(identifier, (int, str)):
            raise ValidationError(f"Bad user_id, expected int|str got {type(identifier)}.")

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

    def check_user_role(self, req_user: User, role: str, user_to_update: User = None) -> str:
        """Given a users role, check that it exist and that the user can pass the role on to the recipient."""
        role = self.check_str(role, "role")
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

    def validate_password_token(self, token: str) -> UserPasswordToken:
        """Validates the create first time password link"""
        self.check_str(token, "token")

        with session_scope() as session:
            password_token = session.query(UserPasswordToken).filter_by(token=token).first()

        if password_token is None:
            raise ValidationError("Invite token does not exist or has expired.")
        else:
            return password_token
