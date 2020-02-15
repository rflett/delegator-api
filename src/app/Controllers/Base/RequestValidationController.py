import datetime
import typing

from flask import request, current_app
from sqlalchemy import func, exists, and_
from validate_email import validate_email

from app.Controllers.Base import ObjectValidationController
from app.Extensions.Errors import ValidationError, ResourceNotFoundError
from app.Extensions.Database import session_scope
from app.Models import TaskType, TaskTypeEscalation, User, Task, Organisation, OrgSetting, TaskLabel
from app.Services import UserService

user_service = UserService()


class RequestValidationController(ObjectValidationController):
    @staticmethod
    def validate_create_org_request() -> str:
        """ Validates a create org request body """
        request_body = request.get_json()
        org_name = request_body["org_name"]

        with session_scope() as session:
            org_exists = session.query(exists().where(func.lower(Organisation.name) == func.lower(org_name))).scalar()

        if org_exists:
            raise ValidationError("That organisation already exists.")
        else:
            return org_name

    def validate_create_user_request(self, req_user: User, request_body: dict) -> None:
        """
        Validates a create user request body
        :param req_user:        The user making the request
        :param request_body:    The request body from the create user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        # check email
        email = request_body.get("email")
        self.validate_email(email)

        self.check_user_id(email, should_exist=False)
        self.check_user_role(req_user, request_body.get("role_id"))
        self.check_str(request_body.get("first_name"), "first_name")
        self.check_str(request_body.get("last_name"), "last_name")
        self.check_optional_str(request_body.get("job_title"), "job_title")
        self.check_user_disabled(request_body.get("disabled"))

    def validate_delay_task_request(self, **kwargs) -> tuple:
        """ Validates the transition task request """
        request_body = request.get_json()
        task = self.check_task_id(request_body.get("task_id"), kwargs["req_user"].org_id)
        if task.assignee is not None:
            self.check_auth_scope(task.assignees, **kwargs)
        delay_for = self.check_int(request_body.get("delay_for"), "delay_for")
        try:
            return task, delay_for, self.check_str(request_body["reason"], "reason")
        except KeyError:
            return task, delay_for, None

    def validate_delete_user(self, user_id: int, **kwargs) -> User:
        """Validates the delete user request"""
        user = self.check_user_id(user_id, should_exist=True)
        self.check_auth_scope(user, **kwargs)
        if user_service.is_user_only_org_admin(user):
            raise ValidationError("Can't delete the only remaining Administrator")
        return user

    def validate_drop_task(self, task_id: int, **kwargs) -> Task:
        """Validates the assign task request
        :param: users_org_id:   The org id of the user making the request
        :param task_id:         The id of the task to drop
        :return:                Response if invalid, else a complex dict
        """
        task = self.check_task_id(task_id, kwargs["req_user"].org_id)

        if task.assignee is None:
            raise ValidationError("Can't drop task because it is not assigned to anyone.")
        else:
            self.check_auth_scope(task.assignees, **kwargs)
            return task

    def validate_email(self, email: str) -> bool:
        """
        Validates an email address. It checks to make sure it's a string, and calls the
        validate_email package which compares it to a huge regex. This package has support
        for MX record check.
        :param email:   The email to validate
        :return:        True if the email is valid, or a Flask Response.
        """
        if validate_email(self.check_str(email, "email")) is False:
            raise ValidationError("Invalid email")
        return True

    @staticmethod
    def validate_get_transitions(users_org_id: int) -> typing.List[Task]:
        """Validates the get task available task transitions request"""
        with session_scope() as session:
            tasks = session.query(Task).filter_by(org_id=users_org_id).all()
        return tasks

    def validate_get_user(self, user_id: int, **kwargs) -> User:
        """Validates the get user request"""
        user = self.check_user_id(user_id, should_exist=True)
        self.check_auth_scope(user, **kwargs)
        return user

    def validate_get_user_activity(self, user_id: int, **kwargs) -> User:
        """Validates the get user activity request"""
        user = self.check_user_id(user_id, should_exist=True)
        self.check_auth_scope(user, **kwargs)
        return user

    @staticmethod
    def validate_password(password: str) -> str:
        """
        Validates a password. Makes sure it's a string, and can do a strength check.
        :param password:    The password to check
        :return:            True if password is valid, or a Flask Response
        """
        if not isinstance(password, str):
            raise ValidationError(f"Bad password expected str got {type(password)}")
        # password_check = self.check_password_reqs(password)
        return password

    def validate_time_period(self, request_body: dict) -> typing.Tuple[datetime.datetime, datetime.datetime]:
        """ Validate that two dates are a valid comparision period """
        # check they exist in the request and can be converted to dates
        try:
            _start_period = self.check_str(request_body["start_period"], "start_period")
            _end_period = self.check_str(request_body["end_period"], "end_period")
            start_period = datetime.datetime.strptime(_start_period, current_app.config["REQUEST_DATE_FORMAT"])
            end_period = datetime.datetime.strptime(_end_period, current_app.config["REQUEST_DATE_FORMAT"])
        except KeyError as e:
            raise ValidationError(f"Missing {e} from request body")
        except ValueError:
            raise ValidationError(
                "Couldn't convert start_period|end_period to datetime.datetime, make sure they're "
                f"in the format {current_app.config['REQUEST_DATE_FORMAT']}"
            )

        # start must be before end
        if end_period < start_period:
            raise ValidationError("start_period must be before end_period")

        # start period can't be in the future
        if start_period > datetime.datetime.utcnow():
            raise ValidationError("start_period is in the future")

        return start_period, end_period

    def validate_transition_task(self, **kwargs) -> Task:
        """ Validates the transition task request """
        request_body = request.get_json()
        task = self.check_task_id(request_body["task_id"], kwargs["req_user"].org_id)
        if task.assignee is not None:
            self.check_auth_scope(task.assignees, **kwargs)
        self.check_task_status(request_body["task_status"])
        return task

    def validate_update_org_request(self, req_user: User, request_body: dict) -> str:
        """ Validates a create org request body """
        org_name = self.check_str(request_body.get("org_name"), "org_name")
        org_id = self.check_int(request_body.get("org_id"), "org_id")

        with session_scope() as session:
            # check org exists
            org = session.query(Organisation).filter_by(id=org_id).first()
            if org is None:
                raise ResourceNotFoundError("That organisation doesn't exist.")

            # check that it's the user's org
            if req_user.org_id != org.id:
                raise ValidationError("You can only update your own organisation's name.")

            # check an org with that name doesn't exist already
            org_name_exists = session.query(
                exists().where(
                    and_(func.lower(Organisation.name) == func.lower(org_name), Organisation.id != req_user.org_id)
                )
            ).scalar()

            if org_name_exists:
                raise ValidationError("That organisation name already exists.")

        return org_name

    def validate_update_user_request(self, request_body: dict, **kwargs) -> dict:
        """  Validates an update user request body """
        user_to_update = self.check_user_id(request_body.get("id"), should_exist=True)
        self.check_auth_scope(user_to_update, **kwargs)
        return {
            "id": user_to_update.id,
            "first_name": self.check_str(request_body.get("first_name"), "first_name"),
            "last_name": self.check_str(request_body.get("last_name"), "last_name"),
            "role": self.check_user_role(kwargs["req_user"], request_body.get("role_id"), user_to_update),
            "job_title": self.check_optional_str(request_body.get("job_title"), "job_title"),
            "disabled": self.check_user_disabled(request_body.get("disabled")),
        }

    def validate_resend_welcome_request(self, request_body: dict) -> typing.Tuple[User, str]:
        """Validate the resend welcome request"""
        user = self.check_user_id(request_body.get("user_id"), should_exist=True)

        # check if invite accepted
        token = user.get_password_token()
        if user.invite_accepted() or token is None:
            raise ValidationError("User has already accepted their invitation.")
        else:
            return user, token
