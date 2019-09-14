import datetime
import dateutil
import typing

from sqlalchemy import exists, and_, func
from validate_email import validate_email

from app import logger, app, session_scope
from app.Exceptions import ValidationError, ResourceNotFoundError, AuthorizationError
from app.Models import TaskType, TaskTypeEscalation, Task, OrgSetting, UserSetting, Organisation, User, TaskPriority, \
    TaskStatus
from app.Models.Enums import NotificationTokens
from app.Models.RBAC import Role


def _check_auth_scope(affected_user: User, **kwargs):
    """Compares a users scope against the action they're trying to do"""
    if kwargs['auth_scope'] == 'SELF' and kwargs['req_user'].id != affected_user.id:
        raise AuthorizationError(f"User {kwargs['req_user'].id} can only perform this action on themselves.")
    elif kwargs['auth_scope'] == 'ORG' and kwargs['req_user'].org_id != affected_user.org_id:
        raise AuthorizationError(f"User {kwargs['req_user'].id} can only perform this"
                                 f" action within their organisation.")


def _check_int(param: int, param_name: str) -> int:
    """Ensures the param is an int and is positive
    In python bools are ints, so we need to checks that it's a bool before we check that it's an int"""
    if isinstance(param, bool):
        raise ValidationError(f"Bad {param_name}, expected int got {type(param)}.")
    if not isinstance(param, int):
        raise ValidationError(f"Bad {param_name}, expected int got {type(param)}.")
    if param < 0:
        raise ValidationError(f"{param_name} is negative.")
    return param


def _check_str(param: str, param_name: str) -> str:
    """Checks that the param is a str, has more than 0 chars in it, and returns the stripped str"""
    if not isinstance(param, str):
        raise ValidationError(f"Bad {param_name}, expected str got {type(param)}.")
    if len(param.strip()) == 0:
        raise ValidationError(f"{param_name} is required.")
    return param.strip()


def _check_password_reqs(password: str) -> bool:
    """ Ensures a password meets minimum security requirements. """
    min_length = 6
    min_special_chars = 1
    min_caps = 1
    special_chars = r' !#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    if len(password) < min_length:
        raise ValidationError(f"Password length less than {min_length}.")
    if len([char for char in password if char in special_chars]) < min_special_chars:
        raise ValidationError(f"Password requires more than {min_special_chars} special character(s).")
    if sum(1 for c in password if c.isupper()) < min_caps:
        raise ValidationError(f"Password requires more than {min_caps} capital letter(s).")
    return True


def _check_user_id(
        identifier: typing.Union[str, int],
        should_exist: typing.Optional[bool] = None) -> typing.Union[None, User]:
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

    return user


def _check_user_role(req_user: User, role: str, user_to_update: User = None) -> str:
    role = _check_str(role, 'role')
    with session_scope() as session:
        _role = session.query(Role).filter_by(id=role).first()
    if _role is None:
        raise ResourceNotFoundError(f"Role {role} doesn't exist")
    elif _role.rank < req_user.roles.rank:
        raise AuthorizationError("You cannot assign a role that has more privileges than you do.")
    elif user_to_update is not None and user_to_update.roles.rank < req_user.roles.rank:
        raise AuthorizationError("You cannot update a user who is more privileged than you.")
    else:
        return _role.id


def _check_user_job_title(job_title: typing.Optional[str]) -> typing.Union[None, str]:
    if job_title is not None:
        return _check_str(job_title, 'job_title')
    else:
        return job_title


def _check_user_disabled(disabled: typing.Optional[datetime.datetime]) -> typing.Union[None, datetime.datetime]:
    if disabled is not None:
        try:
            disabled = datetime.datetime.strptime(disabled, app.config['REQUEST_DATE_FORMAT'])
            return disabled
        except ValueError:
            raise ValidationError(f"Couldn't convert disabled {disabled} to datetime.datetime, please ensure it is "
                                  f"in the format {app.config['REQUEST_DATE_FORMAT']}")


def _check_task_id(task_id: int, org_id: int) -> Task:
    task_id = _check_int(task_id, 'task_id')

    with session_scope() as session:
        task = session.query(Task).filter_by(id=task_id, org_id=org_id).first()

    if task is None:
        raise ResourceNotFoundError(f"Task {task_id} doesn't exist")
    else:
        return task


def _check_task_type_id(task_type_id: int) -> int:
    task_type_id = _check_int(task_type_id, 'task_type_id')

    with session_scope() as session:
        if not session.query(exists().where(TaskType.id == task_type_id)).scalar():
            raise ResourceNotFoundError(f"Task type {task_type_id} doesn't exist")

    return task_type_id


def _check_task_status(task_status: str) -> str:
    task_status = _check_str(task_status, 'task_status')

    with session_scope() as session:
        if not session.query(exists().where(TaskStatus.status == task_status)).scalar():
            raise ResourceNotFoundError(f"Task status {task_status} doesn't exist")

    return task_status.strip()


def _check_task_description(description: typing.Optional[str]) -> typing.Union[None, str]:
    if description is not None:
        return _check_str(description, 'task_description')
    return description


def _check_task_estimate(time_estimate: typing.Optional[int]) -> typing.Union[None, int]:
    if time_estimate is not None:
        return _check_int(time_estimate, 'task_time_estimate')
    return time_estimate


def _check_task_due_time(due_time_str: typing.Optional[str]) -> typing.Union[None, datetime.datetime]:
    if due_time_str is not None:
        try:
            due_time_parsed = dateutil.parser.parse(due_time_str)
            # check due time is not in the past
            if due_time_parsed < datetime.datetime.now(datetime.timezone.utc):
                raise ValidationError("Due time is in the past.")
            return due_time_parsed
        except ValueError as e:
            logger.error(str(e))
            raise ValidationError(f"Could not parse due_time {due_time_str} to date.")
    return None


def _check_task_assignee(assignee: typing.Optional[int], **kwargs) -> typing.Union[int, None]:
    if assignee is not None:
        user = _check_user_id(assignee, should_exist=True)
        _check_auth_scope(user, **kwargs)
        return user.id
    else:
        return None


def _check_task_priority(priority: int) -> int:
    priority = _check_int(priority, 'task_priority')

    with session_scope() as session:
        if not session.query(exists().where(TaskPriority.priority == priority)).scalar():
            raise ResourceNotFoundError(f"Priority {priority} doesn't exist")

    return priority


def _check_escalation(task_type_id: int, display_order: int, should_exist: bool) -> None:
    with session_scope() as session:
        escalation_exists = session.query(exists().where(
                and_(
                    TaskTypeEscalation.task_type_id == task_type_id,
                    TaskTypeEscalation.display_order == display_order
                )
            )).scalar()
        if should_exist and not escalation_exists:
            raise ResourceNotFoundError(f"Task type escalation {task_type_id}:{display_order} doesn't exist")
        elif not should_exist and escalation_exists:
            raise ValidationError(f"Task type escalation {task_type_id}:{display_order} already exists.")


class ValidationController(object):
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validates an email address. It checks to make sure it's a string, and calls the
        validate_email package which compares it to a huge regex. This package has support
        for MX record check.
        :param email:   The email to validate
        :return:        True if the email is valid, or a Flask Response.
        """
        if validate_email(_check_str(email, 'email')) is False:
            raise ValidationError("Invalid email")
        return True

    @staticmethod
    def validate_password(password: str) -> str:
        """
        Validates a password. Makes sure it's a string, and can do a strength check.
        :param password:    The password to check
        :return:            True if password is valid, or a Flask Response
        """
        if not isinstance(password, str):
            raise ValidationError(f"Bad password expected str got {type(password)}")
        # password_check = _check_password_reqs(password)
        return password

    @staticmethod
    def validate_create_task_type_request(request_body: dict, **kwargs) -> typing.Tuple[str, typing.Optional[TaskType]]:
        """ Validates a create task type request body """
        label = _check_str(request_body.get('label'), 'label')

        # check if it exists and needs enabling
        with session_scope() as session:
            task_type = session.query(TaskType).filter(
                func.lower(TaskType.label) == func.lower(label),
                TaskType.org_id == kwargs['req_user'].org_id
            ).first()
            if task_type is None:
                return label, None
            else:
                return label, task_type

    @staticmethod
    def validate_update_task_type_request(org_id: int, request_body: dict) -> typing.Tuple[TaskType, list]:
        """ Validates an update task type request body """
        # check label and that escalations are in the request
        label = _check_str(request_body.get('label'), 'label')

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
                "display_order": _check_int(escalation.get('display_order'), 'display_order'),
                "delay": _check_int(escalation.get('delay'), 'delay'),
                "from_priority": _check_task_priority(escalation.get('from_priority')),
                "to_priority": _check_task_priority(escalation.get('to_priority'))
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
                    _check_escalation(
                        task_type_id=task_type.id,
                        display_order=esc_attrs['display_order'],
                        should_exist=True
                    )
                    esc_attrs['action'] = 'update'
                else:
                    # validate create
                    _check_escalation(
                        task_type_id=task_type.id,
                        display_order=esc_attrs['display_order'],
                        should_exist=False
                    )
                    esc_attrs['action'] = 'create'

            valid_escalations.append(esc_attrs)

        return task_type, valid_escalations

    @staticmethod
    def validate_disable_task_type_request(task_type_id: int) -> TaskType:
        """ Validates the disable task request """
        type_id = _check_int(task_type_id, 'task_type_id')

        with session_scope() as session:
            task_type = session.query(TaskType).filter_by(id=type_id).first()

        if task_type is None:
            raise ResourceNotFoundError(f"Task type {task_type_id} doesn't exist.")
        else:
            return task_type

    @staticmethod
    def validate_create_user_request(req_user: User, request_body: dict) -> None:
        """
        Validates a create user request body
        :param req_user:        The user making the request
        :param request_body:    The request body from the create user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        # check email
        email = request_body.get('email')
        ValidationController.validate_email(email)

        _check_user_id(request_body.get('email'), should_exist=False)
        _check_user_role(req_user, request_body.get('role_id'))
        _check_str(request_body.get('first_name'), 'first_name')
        _check_str(request_body.get('last_name'), 'last_name')
        _check_user_job_title(request_body.get('job_title'))
        _check_user_disabled(request_body.get('disabled'))

    @staticmethod
    def validate_create_signup_user(request_body: dict) -> dict:
        """ Validates creating a user from the signup page """
        # check email
        email = request_body.get('email')
        ValidationController.validate_email(email)

        return {
            "email": _check_user_id(email, should_exist=False),
            "password": ValidationController.validate_password(request_body.get('password')),
            "role": app.config['SIGNUP_ROLE'],
            "first_name": _check_str(request_body.get('first_name'), 'first_name'),
            "last_name": _check_str(request_body.get('last_name'), 'last_name'),
            "job_title": _check_user_job_title(request_body.get('job_title')),
            "disabled": _check_user_disabled(request_body.get('disabled'))
        }

    @staticmethod
    def validate_update_user_request(request_body: dict, **kwargs) -> dict:
        """  Validates an update user request body """
        user_to_update = _check_user_id(request_body.get('id'), should_exist=True)
        _check_auth_scope(user_to_update, **kwargs)
        return {
            "id": user_to_update.id,
            "first_name": _check_str(request_body.get('first_name'), 'first_name'),
            "last_name": _check_str(request_body.get('last_name'), 'last_name'),
            "role": _check_user_role(kwargs['req_user'], request_body.get('role_id'), user_to_update),
            "job_title": _check_user_job_title(request_body.get('job_title')),
            "disabled": _check_user_disabled(request_body.get('disabled'))
        }

    @staticmethod
    def validate_create_org_request(request_body: dict) -> str:
        """ Validates a create org request body """
        org_name = _check_str(request_body.get('org_name'), 'org_name')

        with session_scope() as session:
            org_exists = session.query(exists().where(
                    func.lower(Organisation.name) == func.lower(org_name)
            )).scalar()

        if org_exists:
            raise ValidationError("That organisation already exists.")
        else:
            return org_name

    @staticmethod
    def validate_update_org_request(req_user: User, request_body: dict) -> str:
        """ Validates a create org request body """
        org_name = _check_str(request_body.get('org_name'), 'org_name')
        org_id = _check_int(request_body.get('org_id'), 'org_id')

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
    def validate_create_task_request(request_body: dict, **kwargs) -> dict:
        """Validates a task request body
        :param request_body:    The request body from the create task request
        :return:                Response if the request body contains invalid values, or the TaskRequest dataclass
        """
        return {
            'type': _check_task_type_id(task_type_id=request_body.get('type_id')),
            'description': _check_task_description(request_body.get('description')),
            'status': _check_task_status(request_body.get('status')),
            'time_estimate': _check_task_estimate(request_body.get('time_estimate')),
            'due_time': _check_task_due_time(request_body.get('due_time')),
            'assignee': _check_task_assignee(request_body.get('assignee'), **kwargs),
            'priority': _check_task_priority(request_body.get('priority'))
        }

    @staticmethod
    def validate_update_task_request(request_body: dict, **kwargs) -> dict:
        """Validates a user request body
        :param request_body:    The request body from the update user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        task = _check_task_id(request_body.get('id'), kwargs['req_user'].org_id)
        return {
            'task': task,
            'type': _check_task_type_id(request_body.get('type_id')),
            'description': _check_task_description(request_body.get('description')),
            'status': _check_task_status(request_body.get('status')),
            'time_estimate': _check_task_estimate(request_body.get('time_estimate')),
            'due_time': _check_task_due_time(request_body.get('due_time')),
            'assignee': _check_task_assignee(request_body.get('assignee'), **kwargs),
            'priority': _check_task_priority(request_body.get('priority'))
        }

    @staticmethod
    def validate_assign_task(request_body: dict, **kwargs) -> tuple:
        """Validates the assign task request
        :param: users_org_id:   The org id of the user making the request
        :param request_body:    The request body from the update task request
        :return:                Response if invalid, else a complex dict
        """
        task = _check_task_id(request_body.get('task_id'), kwargs['req_user'].org_id)
        assignee_id = _check_task_assignee(request_body.get('assignee'), **kwargs)

        return task, assignee_id

    @staticmethod
    def validate_drop_task(task_id: int, **kwargs) -> Task:
        """Validates the assign task request
        :param: users_org_id:   The org id of the user making the request
        :param task_id:         The id of the task to drop
        :return:                Response if invalid, else a complex dict
        """
        task = _check_task_id(task_id, kwargs['req_user'].org_id)

        if task.assignee is None:
            raise ValidationError("Can't drop task because it is not assigned to anyone.")
        else:
            _check_auth_scope(task.assignee, **kwargs)
            return task

    @staticmethod
    def validate_cancel_task(task_id: int, **kwargs) -> Task:
        """Validates the cancel task request"""
        task = _check_task_id(task_id, kwargs['req_user'].org_id)
        _check_auth_scope(task.assignees, **kwargs)
        return task

    @staticmethod
    def validate_transition_task(request_body: dict, **kwargs) -> tuple:
        """ Validates the transition task request """
        task = _check_task_id(request_body.get('task_id'), kwargs['req_user'].org_id)
        if task.assignee is not None:
            _check_auth_scope(task.assignee, **kwargs)
        task_status = _check_task_status(request_body.get('task_status'))
        return task, task_status

    @staticmethod
    def validate_get_transitions(users_org_id: int, task_id: int) -> Task:
        """Validates the get task available task transitions request"""
        return _check_task_id(task_id, users_org_id)

    @staticmethod
    def validate_update_org_settings_request(org_id: int, request_body: dict) -> OrgSetting:
        """ Validates updating org settings """
        from decimal import Decimal

        org_setting_obj = OrgSetting(org_id=Decimal(org_id))
        for k, v in request_body.items():
            org_setting_obj.__setattr__(k, v)

        return org_setting_obj

    @staticmethod
    def validate_delay_task_request(request_body: dict, **kwargs) -> tuple:
        """ Validates the transition task request """
        task = _check_task_id(request_body.get('task_id'), kwargs['req_user'].org_id)
        if task.assignee is not None:
            _check_auth_scope(task.assignee, **kwargs)
        delay_for = _check_int(request_body.get('delay_for'), 'delay_for')
        try:
            return task, delay_for, _check_str(request_body['reason'], 'reason')
        except KeyError:
            return task, delay_for, None

    @staticmethod
    def validate_register_token_request(request_body: dict) -> tuple:
        """ Validate the request payload for registering a notification token """
        token_type = _check_str(request_body.get('token_type'), 'token_type')

        if token_type not in NotificationTokens.TOKENS:
            raise ValidationError(f"Token type {token_type} not supported: "
                                  f"supported types are: {NotificationTokens.TOKENS}")

        token = _check_str(request_body.get('token'), 'token')

        return token_type, token

    @staticmethod
    def validate_deregister_token_request(request_body: dict) -> str:
        """ Validate the request payload for registering a notification token """
        token_type = _check_str(request_body.get('token_type'), 'token_type')

        if token_type in NotificationTokens.TOKENS:
            return token_type
        else:
            raise ValidationError(f"Token type {token_type} not supported: "
                                  f"supported types are: {NotificationTokens.TOKENS}")

    @staticmethod
    def validate_time_period(request_body: dict) -> typing.Tuple[datetime.datetime, datetime.datetime]:
        """ Validate that two dates are a valid comparision period """
        # check they exist in the request and can be converted to dates
        try:
            _start_period = _check_str(request_body['start_period'], 'start_period')
            _end_period = _check_str(request_body['end_period'], 'end_period')
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

    @staticmethod
    def validate_get_user(user_id: int, **kwargs) -> User:
        """Validates the get user request"""
        user = _check_user_id(user_id, should_exist=True)
        _check_auth_scope(user, **kwargs)
        return user

    @staticmethod
    def validate_delete_user(user_id: int, **kwargs) -> User:
        """Validates the delete user request"""
        user = _check_user_id(user_id, should_exist=True)
        _check_auth_scope(user, **kwargs)
        return user

    @staticmethod
    def validate_get_user_activity(user_id: int, **kwargs) -> User:
        """Validates the get user activity request"""
        user = _check_user_id(user_id, should_exist=True)
        _check_auth_scope(user, **kwargs)
        return user
