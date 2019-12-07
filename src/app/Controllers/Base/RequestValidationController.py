import datetime
import typing

from flask import request
from sqlalchemy import func, exists, and_
from validate_email import validate_email

from app import app, session_scope
from app.Controllers.Base import ObjectValidationController
from app.Exceptions import ValidationError, ResourceNotFoundError
from app.Models import TaskType, TaskTypeEscalation, User, Task, Organisation, OrgSetting, UserInviteLink, TaskLabel
from app.Services import UserService

user_service = UserService()


class RequestValidationController(ObjectValidationController):
    def validate_assign_task(self, request_body: dict, **kwargs) -> tuple:
        """Validates the assign task request
        :param: users_org_id:   The org id of the user making the request
        :param request_body:    The request body from the update task request
        :return:                Response if invalid, else a complex dict
        """
        task = self.check_task_id(request_body.get('task_id'), kwargs['req_user'].org_id)
        assignee_id = self.check_task_assignee(request_body.get('assignee'), **kwargs)

        return task, assignee_id

    def validate_cancel_task(self, task_id: int, **kwargs) -> Task:
        """Validates the cancel task request"""
        task = self.check_task_id(task_id, kwargs['req_user'].org_id)
        self.check_auth_scope(task.assignees, **kwargs)
        return task

    def validate_create_org_request(self, request_body: dict) -> str:
        """ Validates a create org request body """
        org_name = self.check_str(request_body.get('org_name'), 'org_name')

        with session_scope() as session:
            org_exists = session.query(exists().where(
                func.lower(Organisation.name) == func.lower(org_name)
            )).scalar()

        if org_exists:
            raise ValidationError("That organisation already exists.")
        else:
            return org_name

    def validate_create_signup_user(self, request_body: dict) -> dict:
        """ Validates creating a user from the signup page """
        # check email
        email = request_body.get('email')
        self.validate_email(email)

        return {
            "email": self.check_user_id(email, should_exist=False),
            "password": self.validate_password(request_body.get('password')),
            "role": app.config['SIGNUP_ROLE'],
            "first_name": self.check_str(request_body.get('first_name'), 'first_name'),
            "last_name": self.check_str(request_body.get('last_name'), 'last_name'),
            "job_title": self.check_optional_str(request_body.get('job_title'), 'job_title'),
            "disabled": self.check_user_disabled(request_body.get('disabled'))
        }

    def validate_create_task_request(self, request_body: dict, **kwargs) -> dict:
        """Validates a task request body
        :param request_body:    The request body from the create task request
        :return:                Response if the request body contains invalid values, or the TaskRequest dataclass
        """
        return {
            'type': self.check_task_type_id(task_type_id=request_body.get('type_id')),
            'description': self.check_optional_str(request_body.get('description'), 'description'),
            'time_estimate': self.check_optional_int(request_body.get('time_estimate'), 'time_estimate'),
            'scheduled_for': self.check_date(request_body.get('scheduled_for'), 'scheduled_for'),
            'scheduled_notification_period': self.check_optional_int(
                request_body.get('scheduled_notification_period'), 'scheduled_notification_period'
            ),
            'assignee': self.check_task_assignee(request_body.get('assignee'), **kwargs),
            'priority': self.check_task_priority(request_body.get('priority')),
            'labels': self.check_task_labels(request_body.get('labels', []), kwargs['req_user'].org_id)
        }

    def validate_create_task_type_request(
            self,
            request_body: dict,
            **kwargs
    ) -> typing.Tuple[dict, typing.Optional[TaskType]]:
        """ Validates a create task type request body """
        label = self.check_str(request_body.get('label'), 'label')
        request_defaults = {
            "default_description": self.check_optional_str(
                request_body.get('default_description'), 'default_description'
            ),
            "default_time_estimate": self.check_optional_int(
                request_body.get('default_time_estimate'), 'default_time_estimate'
            ),
            "default_priority": self.check_optional_int(request_body.get('default_priority'), 'default_priority')
        }
        defaults = {k: v for k, v in request_defaults.items() if v is not None}

        # check if it exists and needs enabling
        with session_scope() as session:
            task_type = session.query(TaskType).filter(
                func.lower(TaskType.label) == func.lower(label),
                TaskType.org_id == kwargs['req_user'].org_id
            ).first()
            if task_type is None:
                return defaults, None
            else:
                return defaults, task_type

    def validate_create_user_request(self, req_user: User, request_body: dict) -> None:
        """
        Validates a create user request body
        :param req_user:        The user making the request
        :param request_body:    The request body from the create user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        # check email
        email = request_body.get('email')
        self.validate_email(email)

        self.check_user_id(email, should_exist=False)
        self.check_user_role(req_user, request_body.get('role_id'))
        self.check_str(request_body.get('first_name'), 'first_name')
        self.check_str(request_body.get('last_name'), 'last_name')
        self.check_optional_str(request_body.get('job_title'), 'job_title')
        self.check_user_disabled(request_body.get('disabled'))

    def validate_delay_task_request(self, request_body: dict, **kwargs) -> tuple:
        """ Validates the transition task request """
        task = self.check_task_id(request_body.get('task_id'), kwargs['req_user'].org_id)
        if task.assignee is not None:
            self.check_auth_scope(task.assignees, **kwargs)
        delay_for = self.check_int(request_body.get('delay_for'), 'delay_for')
        try:
            return task, delay_for, self.check_str(request_body['reason'], 'reason')
        except KeyError:
            return task, delay_for, None

    def validate_delete_user(self, user_id: int, **kwargs) -> User:
        """Validates the delete user request"""
        user = self.check_user_id(user_id, should_exist=True)
        self.check_auth_scope(user, **kwargs)
        if user_service.is_user_only_org_admin(user):
            raise ValidationError("Can't delete the only remaining Administrator")
        return user

    def validate_disable_task_type_request(self, task_type_id: int) -> TaskType:
        """ Validates the disable task request """
        type_id = self.check_int(task_type_id, 'task_type_id')

        with session_scope() as session:
            task_type = session.query(TaskType).filter_by(id=type_id).first()

        if task_type is None:
            raise ResourceNotFoundError(f"Task type {task_type_id} doesn't exist.")
        else:
            return task_type

    def validate_drop_task(self, task_id: int, **kwargs) -> Task:
        """Validates the assign task request
        :param: users_org_id:   The org id of the user making the request
        :param task_id:         The id of the task to drop
        :return:                Response if invalid, else a complex dict
        """
        task = self.check_task_id(task_id, kwargs['req_user'].org_id)

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
        if validate_email(self.check_str(email, 'email')) is False:
            raise ValidationError("Invalid email")
        return True

    def validate_get_transitions(self, users_org_id: int) -> typing.List[Task]:
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
            _start_period = self.check_str(request_body['start_period'], 'start_period')
            _end_period = self.check_str(request_body['end_period'], 'end_period')
            start_period = datetime.datetime.strptime(_start_period, app.config['REQUEST_DATE_FORMAT'])
            end_period = datetime.datetime.strptime(_end_period, app.config['REQUEST_DATE_FORMAT'])
        except KeyError as e:
            raise ValidationError(f"Missing {e} from request body")
        except ValueError:
            raise ValidationError("Couldn't convert start_period|end_period to datetime.datetime, make sure they're "
                                  f"in the format {app.config['REQUEST_DATE_FORMAT']}")

        # start must be before end
        if end_period < start_period:
            raise ValidationError("start_period must be before end_period")

        # start period can't be in the future
        if start_period > datetime.datetime.utcnow():
            raise ValidationError("start_period is in the future")

        return start_period, end_period

    def validate_transition_task(self, request_body: dict, **kwargs) -> tuple:
        """ Validates the transition task request """
        task = self.check_task_id(request_body.get('task_id'), kwargs['req_user'].org_id)
        if task.assignee is not None:
            self.check_auth_scope(task.assignees, **kwargs)
        task_status = self.check_task_status(request_body.get('task_status'))
        return task, task_status

    def validate_update_org_request(self, req_user: User, request_body: dict) -> str:
        """ Validates a create org request body """
        org_name = self.check_str(request_body.get('org_name'), 'org_name')
        org_id = self.check_int(request_body.get('org_id'), 'org_id')

        with session_scope() as session:
            # check org exists
            org = session.query(Organisation).filter_by(id=org_id).first()
            if org is None:
                raise ResourceNotFoundError("That organisation doesn't exist.")

            # check that it's the user's org
            if req_user.org_id != org.id:
                raise ValidationError("You can only update your own organisation's name.")

            # check an org with that name doesn't exist already
            org_name_exists = session.query(exists().where(
                and_(
                    func.lower(Organisation.name) == func.lower(org_name),
                    Organisation.id != req_user.org_id
                )
            )).scalar()

            if org_name_exists:
                raise ValidationError("That organisation name already exists.")

        return org_name

    @staticmethod
    def validate_update_org_settings_request(org_id: int, request_body: dict) -> OrgSetting:
        """ Validates updating org settings """
        from decimal import Decimal

        org_setting_obj = OrgSetting(org_id=Decimal(org_id))
        for k, v in request_body.items():
            org_setting_obj.__setattr__(k, v)

        return org_setting_obj

    def validate_update_task_request(self, request_body: dict, **kwargs) -> dict:
        """Validates an update task request"""
        task = self.check_task_id(request_body.get('id'), kwargs['req_user'].org_id)
        return {
            'task': task,
            'type': self.check_task_type_id(request_body.get('type_id')),
            'description': self.check_optional_str(request_body.get('description'), 'description'),
            'status': self.check_task_status(request_body.get('status')),
            'time_estimate': self.check_optional_int(request_body.get('time_estimate'), 'time_estimate'),
            'scheduled_for': self.check_date(request_body.get('scheduled_for'), 'scheduled_for'),
            'scheduled_notification_period': self.check_optional_int(
                request_body.get('scheduled_notification_period'), 'scheduled_notification_period'
            ),
            'assignee': self.check_task_assignee(request_body.get('assignee'), **kwargs),
            'priority': self.check_task_priority(request_body.get('priority')),
            'labels': self.check_task_labels(request_body.get('labels', []), kwargs['req_user'].org_id)
        }

    def validate_update_task_type_request(self, org_id: int, request_body: dict) -> typing.Tuple[TaskType, dict, list]:
        """ Validates an update task type request body """
        # check label and that escalations are in the request
        label = self.check_str(request_body.get('label'), 'label')

        defaults = {
            "default_description": self.check_optional_str(
                request_body.get('default_description'), 'default_description'
            ),
            "default_time_estimate": self.check_optional_int(
                request_body.get('default_time_estimate'), 'default_time_estimate'
            ),
            "default_priority": self.check_optional_int(request_body.get('default_priority'), 'default_priority')
        }

        # check that the task type exists
        with session_scope() as session:
            task_type = session.query(TaskType).filter_by(id=request_body['id'], org_id=org_id).first()
            if task_type is None:
                raise ResourceNotFoundError(f"Task type {label} doesn't exist.")

            if task_type.disabled is not None:
                raise ValidationError(f"Task type {label} is disabled.")

            # check if it's a new label and it already exists
            label_exists = session.query(exists().where(
                and_(
                    func.lower(TaskType.label) == func.lower(label),
                    TaskType.org_id == org_id
                )
            )).scalar()

            if task_type.label != label and label_exists:
                raise ValidationError(f"{task_type.label} cannot be renamed to {label} because a task type with "
                                      f"this name already exists.")

        # check the escalations
        if not isinstance(request_body.get('escalation_policies'), list):
            raise ValidationError(f"Missing escalation_policies from update task type request")

        valid_escalations = []

        for escalation in request_body['escalation_policies']:
            esc_attrs = {
                "display_order": self.check_int(escalation.get('display_order'), 'display_order'),
                "delay": self.check_int(escalation.get('delay'), 'delay'),
                "from_priority": self.check_task_priority(escalation.get('from_priority')),
                "to_priority": self.check_task_priority(escalation.get('to_priority'))
            }

            with session_scope() as session:
                escalation_exists = session.query(exists().where(
                    and_(
                        TaskTypeEscalation.task_type_id == task_type.id,
                        TaskTypeEscalation.display_order == esc_attrs['display_order']
                    )
                )).scalar()

                if escalation_exists:
                    # validate update
                    self.check_escalation(
                        task_type_id=task_type.id,
                        display_order=esc_attrs['display_order'],
                        should_exist=True
                    )
                    esc_attrs['action'] = 'update'
                else:
                    # validate create
                    self.check_escalation(
                        task_type_id=task_type.id,
                        display_order=esc_attrs['display_order'],
                        should_exist=False
                    )
                    esc_attrs['action'] = 'create'

            valid_escalations.append(esc_attrs)

        return task_type, defaults, valid_escalations

    def validate_update_user_request(self, request_body: dict, **kwargs) -> dict:
        """  Validates an update user request body """
        user_to_update = self.check_user_id(request_body.get('id'), should_exist=True)
        self.check_auth_scope(user_to_update, **kwargs)
        return {
            "id": user_to_update.id,
            "first_name": self.check_str(request_body.get('first_name'), 'first_name'),
            "last_name": self.check_str(request_body.get('last_name'), 'last_name'),
            "role": self.check_user_role(kwargs['req_user'], request_body.get('role_id'), user_to_update),
            "job_title": self.check_optional_str(request_body.get('job_title'), 'job_title'),
            "disabled": self.check_user_disabled(request_body.get('disabled'))
        }

    def validate_password_setup_request(self) -> UserInviteLink:
        """Validates the create first time password link"""
        try:
            token = request.args['invtkn']
            self.check_str(token, 'token')
        except KeyError:
            raise ValidationError("Missing invite token from request.")

        with session_scope() as session:
            invite_link = session.query(UserInviteLink).filter_by(token=token).first()

        if invite_link is None:
            raise ValidationError("Invite token does not exist or has expired.")
        else:
            return invite_link

    def validate_create_task_label_request(self, request_body: dict) -> typing.Tuple[str, str]:
        """Validates that the incoming task label is valid"""
        label = self.check_str(request_body.get('label'), 'label')
        colour = self.check_str(request_body.get('colour'), 'colour')
        return label, colour

    def validate_update_task_labels_request(self, request_body: dict, org_id: int) -> TaskLabel:
        """Validates that the incoming task labels are valid"""
        label_id = self.check_int(request_body.get('id'), 'id')
        self.check_str(request_body.get('label'), 'label')
        self.check_str(request_body.get('colour'), 'colour')

        with session_scope() as session:
            task_label = session.query(TaskLabel).filter_by(id=label_id, org_id=org_id).first()

        if task_label is None:
            raise ResourceNotFoundError("Task label doesn't exist.")
        else:
            return task_label

    def validate_delete_task_labels_request(self, request_body: dict, org_id: int) -> TaskLabel:
        """Validates that the incoming task labels are valid"""
        label_id = self.check_int(request_body.get('id'), 'id')

        with session_scope() as session:
            task_label = session.query(TaskLabel).filter_by(id=label_id, org_id=org_id).first()

        if task_label is None:
            raise ResourceNotFoundError("Task label doesn't exist.")
        else:
            return task_label

    def validate_silence_notifications_request(self, request_body: dict) -> typing.Tuple[int, int]:
        """Validates the silencing notifications"""
        silence_until = self.check_date(request_body.get('silence_until'), 'silence_until')
        silenced_option = self.check_int(request_body.get('silenced_option'), 'silenced_option')
        return int(silence_until.timestamp()), silenced_option
