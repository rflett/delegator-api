from email_validator import validate_email, EmailNotValidError
from flask import request
from sqlalchemy import exists

from app.Controllers.Base import ObjectValidationController
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError
from app.Models.Dao import User, Task


class RequestValidationController(ObjectValidationController):
    def validate_delay_task_request(self, **kwargs) -> Task:
        """Validates the transition task request"""
        request_body = request.get_json()
        task = self.check_task_id(request_body.get("task_id"), kwargs["req_user"].org_id)
        if task.assignee is not None:
            self.check_auth_scope(task.assigned_user, **kwargs)
        return task

    def validate_delete_user(self, user_id: int, **kwargs) -> User:
        """Validates the delete user request"""
        user = self.check_user_id(user_id, should_exist=True)
        self.check_auth_scope(user, **kwargs)
        if user.is_only_org_admin():
            raise ValidationError("Can't delete the only remaining Administrator")
        return user

    def validate_disable_user(self, user_id: int, **kwargs) -> User:
        """Validates the disable user request"""
        user = self.check_user_id(user_id, should_exist=True)
        self.check_auth_scope(user, **kwargs)
        if user.is_only_org_admin():
            raise ValidationError("Can't disable the only remaining Administrator")
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
            self.check_auth_scope(task.assigned_user, **kwargs)
            return task

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validates an email address. It checks to make sure it's a string, and calls the
        validate_email package which compares it to a huge regex. This package has support
        for MX record check.
        :param email:   The email to validate
        :return:        True if the email is valid, or a Flask Response.
        """
        # check the email isn't in use currently
        with session_scope() as session:
            if session.query(exists().where(User.email == email)).scalar():
                raise ValidationError("That email is already in use.")

        # validate the email itself
        try:
            validate_email(email)
        except EmailNotValidError as e:
            raise ValidationError(str(e))

        return True

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
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if len(password) > 64:
            raise ValidationError("Password must be at most 64 characters long")
        return password

    def validate_transition_task(self, **kwargs) -> Task:
        """Validates the transition task request"""
        request_body = request.get_json()
        task = self.check_task_id(request_body["task_id"], kwargs["req_user"].org_id)
        if task.assignee is not None:
            self.check_auth_scope(task.assigned_user, **kwargs)
        return task
