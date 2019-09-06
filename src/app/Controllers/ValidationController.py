import datetime
import dateutil
import typing

from sqlalchemy import exists, and_, func
from validate_email import validate_email

from app import logger, app, session_scope
from app.Exceptions import ValidationError
from app.Models import TaskType, TaskTypeEscalation, Task, OrgSetting, UserSetting, Organisation, User, TaskPriority, \
    TaskStatus
from app.Models.Enums import NotificationTokens
from app.Models.RBAC import Role


def _check_int(param: int, param_name: str) -> int:
    """Ensures the param is an int and is positive
    In python bools are ints, so we need to checks that it's a bool before we check that it's an int"""
    if isinstance(param, bool):
        logger.info(f"Bad {param_name}, expected int got {type(param)}.")
        raise ValidationError(f"Bad {param_name}, expected int got {type(param)}.")
    if not isinstance(param, int):
        logger.info(f"Bad {param_name}, expected int got {type(param)}.")
        raise ValidationError(f"Bad {param_name}, expected int got {type(param)}.")
    if param < 0:
        logger.info(f"{param_name} is negative.")
        raise ValidationError(f"{param_name} is negative.")
    return param


def _check_str(param: str, param_name: str) -> str:
    """Checks that the param is a str, has more than 0 chars in it, and returns the stripped str"""
    if not isinstance(param, str):
        logger.info(f"Bad {param_name}, expected str got {type(param)}.")
        raise ValidationError(f"Bad {param_name}, expected str got {type(param)}.")
    if len(param.strip()) == 0:
        logger.info(f"{param_name} is required.")
        raise ValidationError(f"{param_name} is required.")
    return param.strip()


def _check_password_reqs(password: str) -> bool:
    """ Ensures a password meets minimum security requirements. """
    min_length = 6
    min_special_chars = 1
    min_caps = 1
    special_chars = r' !#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    if len(password) < min_length:
        logger.info(f"password length less than {min_length}.")
        raise ValidationError(f"Password length less than {min_length}.")
    if len([char for char in password if char in special_chars]) < min_special_chars:
        logger.info(f"password requires more than {min_special_chars} special character(s).")
        raise ValidationError(f"Password requires more than {min_special_chars} special character(s).")
    if sum(1 for c in password if c.isupper()) < min_caps:
        logger.info(f"password requires more than {min_caps} capital letter(s).")
        raise ValidationError(f"Password requires more than {min_caps} capital letter(s).")
    logger.info(f"password meets requirements")
    return True


def _check_user_id(
        identifier: typing.Union[str, int],
        should_exist: typing.Optional[bool] = None
) -> typing.Union[None, str, int]:
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
                user_exists = session.query(exists().where(func.lower(User.email) == func.lower(identifier))).scalar()
            else:
                user_exists = session.query(exists().where(User.id == identifier)).scalar()

        if should_exist and not user_exists:
            logger.info(f"user {identifier} doesn't exist")
            raise ValidationError(f"user does not exist")
        elif not should_exist and user_exists:
            logger.info(f"user {identifier} already exists")
            raise ValidationError("user already exists")

    return identifier


def _check_user_role(role: str) -> str:
    role = _check_str(role, 'role')
    with session_scope() as session:
        role_exists = session.query(exists().where(Role.id == role)).scalar()
    if not role_exists:
        logger.info(f"Role {role} does not exist")
        raise ValidationError(f"Role {role} does not exist")
    return role


def _check_user_job_title(job_title: typing.Optional[str]) -> typing.Union[None, str]:
    if job_title is not None:
        return _check_str(job_title, 'job_title')
    return job_title


def _check_user_disabled(disabled: typing.Optional[datetime.datetime]) -> typing.Union[None, datetime.datetime]:
    if disabled is not None:
        try:
            disabled = datetime.datetime.strptime(disabled, app.config['REQUEST_DATE_FORMAT'])
            return disabled
        except ValueError:
            raise ValidationError("Couldn't convert disabled to datetime.datetime")


def _check_task_id(task_id: int, org_id: int) -> int:
    task_id = _check_int(task_id, 'task_id')

    with session_scope() as session:
        task_exists = session.query(exists().where(and_(Task.id == task_id, Task.org_id == org_id))).scalar()

    if not task_exists:
        logger.info(f"task {task_id} doesn't exist")
        raise ValidationError(f"task does not exist")

    return task_id


def _check_task_type_id(task_type_id: int, should_exist: typing.Optional[bool] = None) -> int:
    task_type_id = _check_int(task_type_id, 'task_type_id')

    # optionally check if it exists or not
    if should_exist is not None:
        with session_scope() as session:
            task_exists = session.query(exists().where(TaskType.id == task_type_id)).scalar()

        if should_exist and not task_exists:
            logger.info(f"task type id {task_type_id} doesn't exist")
            raise ValidationError(f"task type does not exist")
        elif not should_exist and task_exists:
            logger.info(f"task type id {task_type_id} in org already exists")
            raise ValidationError("task type already exists")

    return task_type_id


def _check_task_status(task_status: str, should_exist: typing.Optional[bool] = None) -> str:
    task_status = _check_str(task_status, 'task_status')

    # optionally check if it exists or not
    if should_exist is not None:

        with session_scope() as session:
            status_exist = session.query(exists().where(TaskStatus.status == task_status)).scalar()

        if should_exist and not status_exist:
            logger.info(f"task status {task_status} doesn't exist")
            raise ValidationError(f"task status {task_status} does not exist")
        elif not should_exist and status_exist:
            logger.info(f"task status {task_status} already exists")
            raise ValidationError(f"task status {task_status} already exists")

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
                logger.info(f"due_time is in the past")
                raise ValidationError("Due time is in the past.")
            return due_time_parsed
        except ValueError as e:
            logger.error(str(e))
            raise ValidationError(f'Could not parse due_time to date.')
    return None


def _check_task_assignee(assignee: typing.Optional[int]) -> typing.Union[int, None]:
    if assignee is not None:
        return _check_user_id(assignee, should_exist=True)
    else:
        return None


def _check_task_priority(priority: int) -> int:
    priority = _check_int(priority, 'task_priority')

    with session_scope() as session:
        if not session.query(exists().where(TaskPriority.priority == priority)).scalar():
            logger.info(f"Priority {priority} does not exist")
            raise ValidationError(f"Priority does not exist")
        else:
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
            logger.info(f"task type escalation {task_type_id}:{display_order} doesn't exist")
            raise ValidationError(f"task type escalation {task_type_id}:{display_order} does not exist")
        elif not should_exist and escalation_exists:
            logger.info(f"task type escalation {task_type_id}:{display_order} already exists")
            raise ValidationError(f"task type escalation {task_type_id}:{display_order} already exists")


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
        if not isinstance(email, str):
            logger.info(f"bad email expected str got {type(email)}")
            raise ValidationError(f"Bad email expected str got {type(email)}")
        if validate_email(email) is False:
            logger.info("email is invalid")
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
            logger.info(f"bad password expected str got {type(password)}")
            raise ValidationError(f"Bad password expected str got {type(password)}")
        # password_check = _check_password_reqs(password)
        return password

    @staticmethod
    def validate_create_task_type_request(
            org_id: int,
            request_body: dict) -> typing.Tuple[str, typing.Optional[TaskType]]:
        """ Validates a create task type request body """
        label = _check_str(request_body.get('label'), 'label')

        # check if it exists and needs enabling
        with session_scope() as session:
            task_type = session.query(TaskType).filter(
                func.lower(TaskType.label) == func.lower(label),
                TaskType.org_id == org_id
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
                raise ValidationError(f"Task type {label} doesn't exist.")

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
            raise ValidationError(f"Task type does not exist.")
        else:
            return task_type

    @staticmethod
    def validate_create_user_request(request_body: dict) -> None:
        """
        Validates a create user request body
        :param request_body:    The request body from the create user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        # check email
        email = request_body.get('email')
        ValidationController.validate_email(email)

        _check_user_id(request_body.get('email'), should_exist=False),
        _check_user_role(request_body.get('role_id')),
        _check_str(request_body.get('first_name'), 'first_name'),
        _check_str(request_body.get('last_name'), 'last_name'),
        _check_user_job_title(request_body.get('job_title')),
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
    def validate_update_user_request(request_body: dict) -> dict:
        """  Validates an update user request body """
        return {
            "id": _check_user_id(request_body.get('id'), should_exist=True),
            "first_name": _check_str(request_body.get('first_name'), 'first_name'),
            "last_name": _check_str(request_body.get('last_name'), 'last_name'),
            "role": _check_user_role(request_body.get('role_id')),
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
                raise ValidationError("That organisation doesn't exist.")

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
    def validate_create_task_request(request_body: dict) -> dict:
        """
        Validates a task request body
        :param request_body:    The request body from the create task request
        :return:                Response if the request body contains invalid values, or the TaskRequest dataclass
        """
        return {
            'type': _check_task_type_id(task_type_id=request_body.get('type_id'), should_exist=True),
            'description': _check_task_description(request_body.get('description')),
            'status': _check_task_status(request_body.get('status'), should_exist=True),
            'time_estimate': _check_task_estimate(request_body.get('time_estimate')),
            'due_time': _check_task_due_time(request_body.get('due_time')),
            'assignee': _check_task_assignee(request_body.get('assignee')),
            'priority': _check_task_priority(request_body.get('priority'))
        }

    @staticmethod
    def validate_update_task_request(org_id: int, request_body: dict) -> dict:
        """
        Validates a user request body
        :param org_id:          The org that the task should be in (from the req user)
        :param request_body:    The request body from the update user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        return {
            'id': _check_task_id(request_body.get('id'), org_id),
            'type': _check_task_type_id(task_type_id=request_body.get('type_id'), should_exist=True),
            'description': _check_task_description(request_body.get('description')),
            'status': _check_task_status(request_body.get('status'), should_exist=True),
            'time_estimate': _check_task_estimate(request_body.get('time_estimate')),
            'due_time': _check_task_due_time(request_body.get('due_time')),
            'assignee': _check_task_assignee(request_body.get('assignee')),
            'priority': _check_task_priority(request_body.get('priority'))
        }

    @staticmethod
    def validate_assign_task(org_id: int, request_body: dict) -> tuple:
        """
        Validates the assign task request
        :param request_body:    The request body from the update task request
        :return:                Response if invalid, else a complex dict
        """
        from app.Controllers import TaskController

        task_id = _check_int(param=request_body.get('task_id'), param_name='task_id')

        try:
            task = TaskController.get_task_by_id(task_id, org_id)
        except ValueError:
            raise ValidationError("Task does not exist.")

        assignee_id = _check_task_assignee(request_body.get('assignee'))

        return task, assignee_id

    @staticmethod
    def validate_drop_task(org_id: int, task_id: int) -> Task:
        """
        Validates the assign task request
        :param task_id:    The id of the task to drop
        :return:           Response if invalid, else a complex dict
        """
        from app.Controllers import TaskController

        task_id = _check_int(param=task_id, param_name='task_id')

        try:
            task = TaskController.get_task_by_id(task_id, org_id)
            if task.assignee is None:
                raise ValidationError("Can't drop task because it is not assigned to anyone.")
            else:
                return task
        except ValueError:
            raise ValidationError("Task does not exist.")

    @staticmethod
    def validate_cancel_task(org_id: int, task_id: int) -> Task:
        """
        Validates the cancel task request
        :param org_id:  The task's org id
        :param task_id: The id of the task to cancel
        :return:        Task object
        :raises:        ValidationError
        """
        from app.Controllers import TaskController

        task_id = _check_int(param=task_id, param_name='task_id')

        try:
            return TaskController.get_task_by_id(task_id, org_id)
        except ValueError:
            raise ValidationError("Task does not exist.")

    @staticmethod
    def validate_transition_task(org_id: int, request_body: dict) -> tuple:
        """ Validates the transition task request """
        from app.Controllers import TaskController

        task_id = _check_int(param=request_body.get('task_id'), param_name='task_id')

        try:
            task = TaskController.get_task_by_id(task_id, org_id)
        except ValueError:
            raise ValidationError("Task does not exist.")

        task_status = _check_task_status(request_body.get('task_status'), should_exist=True)

        return task, task_status

    @staticmethod
    def validate_get_transitions(org_id: int, task_id: int) -> Task:
        """
        Validates the get task available task transitions request
        :param org_id:  Org id of the task
        :param task_id: The task id
        :return:        Task object
        :raises:        ValidationError
        """
        from app.Controllers import TaskController

        task_id = _check_int(param=task_id, param_name='task_id')

        try:
            return TaskController.get_task_by_id(task_id, org_id)
        except ValueError:
            raise ValidationError("Task does not exist.")

    @staticmethod
    def validate_update_user_settings_request(user_id: int, request_body: dict) -> UserSetting:
        """ Validates updating user settings """
        from decimal import Decimal

        user_setting_obj = UserSetting(user_id=Decimal(user_id))
        for k, v in request_body.items():
            user_setting_obj.__setattr__(k, v)

        return user_setting_obj

    @staticmethod
    def validate_update_org_settings_request(org_id: int, request_body: dict) -> OrgSetting:
        """ Validates updating org settings """
        from decimal import Decimal

        org_setting_obj = OrgSetting(org_id=Decimal(org_id))
        for k, v in request_body.items():
            org_setting_obj.__setattr__(k, v)

        return org_setting_obj

    @staticmethod
    def validate_delay_task_request(org_id: int, request_body: dict) -> tuple:
        """ Validates the transition task request """
        from app.Controllers import TaskController

        task_id = _check_int(request_body.get('task_id'), 'task_id')

        delay_for = _check_int(request_body.get('delay_for'), 'delay_for')

        reason = request_body.get('reason')
        if reason is not None:
            reason = _check_str(reason, 'reason')

        try:
            task = TaskController.get_task_by_id(task_id, org_id)
        except ValueError:
            raise ValidationError("Task does not exist.")

        return task, delay_for, reason

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
