import datetime
import dateutil
import typing
from app import logger, g_response, app, session_scope
from app.Models import TaskType, TaskTypeEscalation
from flask import Response
from sqlalchemy import exists, and_
from validate_email import validate_email


def _check_password_reqs(password: str) -> typing.Union[str, bool]:
    """ Ensures a password meets minimum security requirements. """
    min_length = 6
    min_special_chars = 1
    min_caps = 1
    special_chars = r' !#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    if len(password) < min_length:
        logger.info(f"password length less than {min_length}.")
        return f"Password length less than {min_length}."
    if len([char for char in password if char in special_chars]) < min_special_chars:
        logger.info(f"password requires more than {min_special_chars} special character(s).")
        return f"Password requires more than {min_special_chars} special character(s)."
    if sum(1 for c in password if c.isupper()) < min_caps:
        logger.info(f"password requires more than {min_caps} capital letter(s).")
        return f"Password requires more than {min_caps} capital letter(s)."
    logger.info(f"password meets requirements")
    return True


def _check_org_id(
        identifier: typing.Union[str, int],
        should_exist: typing.Optional[bool] = None
) -> typing.Union[str, int, Response]:
    """ Checks an org id """
    from app.Controllers import OrganisationController
    if isinstance(identifier, bool):
        return g_response(f"Bad org_id, expected int|str got {type(identifier)}.", 400)
    if not isinstance(identifier, (int, str)):
        return g_response(f"Bad org_id, expected int|str got {type(identifier)}.", 400)

    # optionally check if it exists or not
    if should_exist is not None:
        org_exists = OrganisationController.org_exists(identifier)
        if should_exist:
            if org_exists:
                if isinstance(identifier, str):
                    return OrganisationController.get_org_by_name(identifier).id
                else:
                    return identifier
            else:
                logger.info(f"org {identifier} doesn't exist")
                return g_response(f"Org does not exist", 400)
        elif not should_exist:
            if org_exists:
                logger.info(f"organisation {identifier} already exists")
                return g_response("Organisation already exists", 400)
    return identifier


def _check_user_id(
        identifier: typing.Union[str, int],
        should_exist: typing.Optional[bool] = None
) -> typing.Union[None, str, int, Response]:
    """ Checks a user id """
    from app.Controllers import UserController
    if isinstance(identifier, bool):
        return g_response(f"Bad org_id, expected int|str got {type(identifier)}.", 400)
    if not isinstance(identifier, (int, str)):
        return g_response(f"Bad org_id, expected int|str got {type(identifier)}.", 400)

    # optionally check if it exists or not
    if should_exist is not None:
        user_exists = UserController.user_exists(identifier)
        if should_exist:
            if not user_exists:
                logger.info(f"user {identifier} doesn't exist")
                return g_response(f"user does not exist", 400)
        elif not should_exist:
            if user_exists:
                logger.info(f"user {identifier} already exists")
                return g_response("user already exists", 400)
    return identifier


def _check_user_first_name(first_name: str) -> typing.Union[str, Response]:
    """ Check a first name """
    if not isinstance(first_name, str):
        logger.info(f"Bad first_name, expected str got {type(first_name)}.")
        return g_response(f"Bad first_name, expected str got {type(first_name)}.", 400)
    if len(first_name.strip()) == 0:
        logger.info(f"first_name is required.")
        return g_response(f"first_name is required.", 400)
    return first_name.strip()


def _check_user_last_name(last_name: str) -> typing.Union[str, Response]:
    """ Check a last name """
    if not isinstance(last_name, str):
        logger.info(f"Bad last_name, expected str got {type(last_name)}.")
        return g_response(f"Bad last_name, expected str got {type(last_name)}.", 400)
    if len(last_name.strip()) == 0:
        logger.info(f"last_name is required.")
        return g_response(f"last_name is required.", 400)
    return last_name.strip()


def _check_user_role(role: str) -> typing.Union[str, Response]:
    """" Check a user role """
    from app.Controllers import AuthController
    if not isinstance(role, str):
        logger.info(f"Bad role, expected str got {type(role)}.")
        return g_response(f"Bad role, expected str got {type(role)}.", 400)
    if len(role.strip()) == 0:
        logger.info(f"role is required.")
        return g_response(f"role is required.", 400)
    if not AuthController.role_exists(role):
        logger.info(f"Role {role} does not exist")
        return g_response(f"Role {role} does not exist", 400)
    return role


def _check_user_job_title(job_title: typing.Optional[str]) -> typing.Union[None, str, Response]:
    """ Check a job title """
    if job_title is not None:
        if not isinstance(job_title, str):
            logger.info(f"Bad job_title, expected str got {type(job_title)}.")
            return g_response(f"Bad job_title, expected str got {type(job_title)}.", 400)
        if len(job_title.strip()) == 0:
            logger.info(f"job_title length is 0.")
            return g_response(f"job_title length is 0.", 400)
        return job_title.strip()
    return job_title


def _check_user_disabled(disabled: typing.Optional[bool]) -> typing.Union[None, bool, Response]:
    """ Check the disabled value """
    if disabled is not None:
        if not isinstance(disabled, bool):
            logger.info(f"Bad disabled, expected bool got {type(disabled)}.")
            return g_response(f"Bad disabled, expected bool got {type(disabled)}.", 400)
    return False


def _check_task_id(task_id: int) -> typing.Union[Response, int]:
    """ Checks a task id """
    from app.Controllers import TaskController
    if isinstance(task_id, bool):
        logger.info(f"Bad task id, expected int got {type(task_id)}.")
        return g_response(f"Bad task id, expected int got {type(task_id)}.", 400)
    if not isinstance(task_id, int):
        logger.info(f"Bad task id, expected int got {type(task_id)}.")
        return g_response(f"Bad task id, expected int got {type(task_id)}.", 400)
    if not TaskController.task_exists(task_id):
        logger.info(f"task {task_id} doesn't exist")
        return g_response(f"task does not exist", 400)
    return task_id


def _check_task_type_id(
        task_type_id: int,
        should_exist: typing.Optional[bool] = None
) -> typing.Union[int, Response]:
    """ Check a task type """
    from app.Controllers import TaskController
    if isinstance(task_type_id, bool):
        logger.info(f"Bad task_type, expected int got {type(task_type_id)}.")
        return g_response(f"Bad task_type, expected int got {type(task_type_id)}.", 400)
    if not isinstance(task_type_id, int):
        logger.info(f"Bad task_type, expected int got {type(task_type_id)}.")
        return g_response(f"Bad task_type, expected int got {type(task_type_id)}.", 400)

    # optionally check if it exists or not
    if should_exist is not None:
        task_exists = TaskController.task_type_exists(task_type_id)
        if should_exist:
            if not task_exists:
                logger.info(f"task type id {task_type_id} doesn't exist")
                return g_response(f"task type does not exist", 400)
        elif not should_exist:
            if task_exists:
                logger.info(f"task type id {task_type_id} in org already exists")
                return g_response("task type already exists", 400)
    return task_type_id


def _check_task_type_label(
        label: str,
        org_id: int,
        should_exist: typing.Optional[bool] = None
) -> typing.Union[str, int, Response]:
    """ Checks a task type label """
    from app.Controllers import TaskController
    if not isinstance(label, str):
        logger.info(f"Bad task type label, expected str got {type(label)}.")
        return g_response(f"Bad task type label, expected str got {type(label)}.", 400)
    if len(label.strip()) == 0:
        logger.info(f"Task type label length is 0")
        return g_response(f"Task type label length is 0.", 400)

    # optionally check if it exists or not
    if should_exist is not None:
        task_type_exists = TaskController.task_type_exists(label, org_id)
        if should_exist:
            if not task_type_exists:
                logger.info(f"task type id {label} in org {org_id} doesn't exist")
                return g_response(f"task type does not exist", 400)
        elif not should_exist:
            if task_type_exists:
                logger.info(f"task type id {label} in org {org_id} already exists")
                return g_response("task type already exists", 400)
    return label


def _check_task_status(
        task_status: str,
        should_exist: typing.Optional[bool] = None
) -> typing.Union[str, Response]:
    """ Check a task status """
    from app.Controllers import TaskController
    if not isinstance(task_status, str):
        logger.info(f"Bad task_status, expected str got {type(task_status)}.")
        return g_response(f"Bad task_status, expected str got {type(task_status)}.", 400)
    if len(task_status.strip()) == 0:
        logger.info(f"status length is 0")
        return g_response(f"status length is 0.", 400)

    # optionally check if it exists or not
    if should_exist is not None:
        task_exists = TaskController.task_status_exists(task_status)
        if should_exist:
            if not task_exists:
                logger.info(f"task status {task_status} doesn't exist")
                return g_response(f"task status {task_status} does not exist", 400)
        elif not should_exist:
            if task_exists:
                logger.info(f"task status {task_status} already exists")
                return g_response(f"task status {task_status} already exists", 400)
    return task_status.strip()


def _check_task_description(description: typing.Optional[str]) -> typing.Union[None, str, Response]:
    """ Check a task description """
    if description is not None:
        if not isinstance(description, str):
            logger.info(f"Bad description, expected str got {type(description)}.")
            return g_response(f"Bad description, expected str got {type(description)}.", 400)
        if len(description.strip()) == 0:
            logger.info(f"description length is 0.")
            return g_response(f"description length is 0.", 400)
        return description.strip()
    return description


def _check_task_estimate(time_estimate: typing.Optional[int]) -> typing.Union[None, int, Response]:
    """ Check a task estimate - estimated seconds to complete """
    if time_estimate is not None:
        if not isinstance(time_estimate, int):
            logger.info(f"Bad estimate, expected int got {type(time_estimate)}.")
            return g_response(f"Bad estimate, expected int got {type(time_estimate)}.", 400)
        if time_estimate < 0:
            logger.info(f"Estimate must be positive.")
            return g_response(f"Estimate must be positive.", 400)
    return time_estimate


def _check_task_due_time(due_time_str: typing.Optional[str]) -> typing.Union[None, datetime.datetime, Response]:
    """ Check the task due time """
    if due_time_str is not None:
        try:
            due_time_parsed = dateutil.parser.parse(due_time_str)
            # check due time is not in the past
            if due_time_parsed < datetime.datetime.utcnow():
                logger.info(f"due_time is in the past")
                return g_response("Due time is in the past.", 400)
            return due_time_parsed
        except ValueError as e:
            logger.error(str(e))
            return g_response(f'Could not parse due_time to date.', 400)
    return None


def _check_task_assignee(assignee: typing.Optional[int]) -> typing.Union[int, Response]:
    """ Check a task assignee """
    from app.Controllers import UserController
    if assignee is not None:
        if not isinstance(assignee, int):
            logger.info(f"Bad assignee, expected int got {type(assignee)}.")
            return g_response(f"Bad assignee, expected int got {type(assignee)}.", 400)
        if not UserController.user_exists(assignee):
            logger.info(f"Assignee {assignee} does not exist")
            return g_response(f"Assignee does not exist", 400)
    return assignee


def _check_task_priority(priority: int) -> typing.Union[int, Response]:
    """ Check a task priority """
    from app.Controllers import TaskController
    if isinstance(priority, bool):
        logger.info(f"Bad priority, expected int got {type(priority)}.")
        return g_response(f"Bad priority, expected int got {type(priority)}.", 400)
    if not isinstance(priority, int):
        logger.info(f"Bad priority, expected int got {type(priority)}.")
        return g_response(f"Bad priority, expected int got {type(priority)}.", 400)
    if not TaskController.task_priority_exists(priority):
        logger.info(f"Priority {priority} does not exist")
        return g_response(f"Priority does not exist", 400)
    return priority


def _check_escalation_delay(delay: int) -> typing.Union[int, Response]:
    """ Check escalation delay """
    if isinstance(delay, bool):
        logger.info(f"Bad priority, expected int got {type(delay)}.")
        return g_response(f"Bad priority, expected int got {type(delay)}.", 400)
    if not isinstance(delay, int):
        logger.info(f"Bad priority, expected int got {type(delay)}.")
        return g_response(f"Bad priority, expected int got {type(delay)}.", 400)
    return delay


def _check_escalation_display_order(order: int) -> typing.Union[int, Response]:
    """ Check escalation display order """
    if isinstance(order, bool):
        logger.info(f"Bad priority, expected int got {type(order)}.")
        return g_response(f"Bad priority, expected int got {type(order)}.", 400)
    if not isinstance(order, int):
        logger.info(f"Bad priority, expected int got {type(order)}.")
        return g_response(f"Bad priority, expected int got {type(order)}.", 400)
    return order


def _check_escalation(
        task_type_id: int,
        display_order: int,
        should_exist: bool
) -> typing.Optional[Response]:
    """ Checks to see if an escalation already exists """
    with session_scope() as session:
        escalation_exists = session.query(exists().where(
            and_(
                TaskTypeEscalation.task_type_id == task_type_id,
                TaskTypeEscalation.display_order == display_order
            ))).scalar()
        if should_exist:
            if not escalation_exists:
                logger.info(f"task type escalation {task_type_id}:{display_order} doesn't exist")
                return g_response(f"task type escalation {task_type_id}:{display_order} does not exist", 400)
        elif not should_exist:
            if escalation_exists:
                logger.info(f"task type escalation {task_type_id}:{display_order} already exists")
                return g_response(f"task type escalation {task_type_id}:{display_order} already exists", 400)


class ValidationController(object):
    @staticmethod
    def validate_email(email: str) -> typing.Union[bool, Response]:
        """
        Validates an email address. It checks to make sure it's a string, and calls the
        validate_email package which compares it to a huge regex. This package has support
        for MX record check.
        :param email:   The email to validate
        :return:        True if the email is valid, or a Flask Response.
        """
        if not isinstance(email, str):
            logger.info(f"bad email expected str got {type(email)}")
            return g_response(f"Bad email expected str got {type(email)}", 400)
        if validate_email(email) is False:
            logger.info("email is invalid")
            return g_response("Invalid email", 400)
        return True

    @staticmethod
    def validate_password(password: str) -> typing.Union[bool, Response]:
        """
        Validates a password. Makes sure it's a string, and can do a strength check.
        :param password:    The password to check
        :return:            True if password is valid, or a Flask Response
        """
        if not isinstance(password, str):
            logger.info(f"bad password expected str got {type(password)}")
            return g_response(f"Bad password expected str got {type(password)}", 400)
        # password_check = _check_password_reqs(password)
        # if isinstance(password_check, str):
        #     return g_response(password_check, 400)
        return True

    @staticmethod
    def validate_create_task_type_request(request_body: dict) -> typing.Union[Response, dict]:
        """
        Validates a task type request body
        :param request_body:    The request body from the create task type request
        :return:                Response if the request body contains invalid values, or the TaskTypeRequest dataclass
        """
        from app.Controllers import TaskController

        org_id = _check_org_id(request_body.get('org_id'), should_exist=True)
        if isinstance(org_id, Response):
            return org_id

        label = _check_task_type_label(request_body.get('label'), org_id)
        if isinstance(label, Response):
            return label

        disabled = None
        if TaskController.task_type_exists(label, org_id):
            # if it's enabled, return exists error, else re-enable it
            if TaskController.task_type_enabled(label, org_id):
                return g_response(f"Task type already exists.")
            disabled = True

        return {
            "org_id": org_id,
            "label": label,
            "disabled": disabled
        }

    @staticmethod
    def validate_disable_task_type_request(task_type_id: int) -> typing.Union[Response, TaskType]:
        """ Validates the disable task request """
        from app.Controllers import TaskController

        type_id = _check_task_type_id(task_type_id=task_type_id)
        if isinstance(type_id, Response):
            return type_id

        try:
            task_type = TaskController.get_task_type_by_id(type_id)
        except ValueError as e:
            logger.warning(str(e))
            return g_response(f"Task type does not exist.")

        return task_type

    @staticmethod
    def validate_create_user_request(request_body: dict, from_signup=False) -> typing.Union[Response, dict]:
        """
        Validates a create user request body
        :param request_body:    The request body from the create user request
        :param from_signup:     Indicates that this validation request came from the signup page, so
                                we should ignore org and role checks. The organisation won't be created yet, this is
                                pre-creation validation. The role will not be provided because the default role
                                will be given.
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        ret = {}

        # check email
        email = request_body.get('email')
        email_check = ValidationController.validate_email(email)
        if isinstance(email_check, Response):
            return email_check
        ret['email'] = _check_user_id(request_body.get('email'), should_exist=False)

        # check password
        password = request_body.get('password')
        password_check = ValidationController.validate_password(password)
        if isinstance(password_check, Response):
            return password_check
        ret['password'] = password

        if from_signup:
            request_body['role'] = app.config['SIGNUP_ROLE']
        elif not from_signup:
            ret['org_id'] = _check_org_id(request_body.get('org_id', request_body.get('org_name')), should_exist=True)
            ret['role'] = _check_user_role(request_body.get('role_name'))

        ret['first_name'] = _check_user_first_name(request_body.get('first_name'))
        ret['last_name'] = _check_user_last_name(request_body.get('last_name'))
        ret['job_title'] = _check_user_job_title(request_body.get('job_title'))
        ret['disabled'] = _check_user_disabled(request_body.get('disabled'))

        # return a response if any ret values are response objects
        for k, v in ret.items():
            if isinstance(v, Response):
                return v

        return ret

    @staticmethod
    def validate_update_user_request(user_id: int, request_body: dict) -> typing.Union[Response, dict]:
        """  Validates an update user request body """
        from app.Controllers import UserController
        ret = {}

        check_user = _check_user_id(user_id, should_exist=True)
        if isinstance(check_user, Response):
            return check_user

        # check email
        email = request_body.get('email')
        email_check = ValidationController.validate_email(email)
        if isinstance(email_check, Response):
            return email_check

        # check email doesn't exist if it's not the same as before
        user = UserController.get_user_by_id(user_id)
        if email != user.email:
            # emails don't match, so check that it doesn't exist
            if UserController.user_exists(email):
                logger.info(f"email {email} already in use")
                return g_response(f"Email already exists.", 400)

        ret['org_id'] = _check_org_id(request_body.get('org_id', request_body.get('org_name')), should_exist=True)
        ret['first_name'] = _check_user_first_name(request_body.get('first_name'))
        ret['last_name'] = _check_user_last_name(request_body.get('last_name'))
        ret['role'] = _check_user_role(request_body.get('role_name'))
        ret['job_title'] = _check_user_job_title(request_body.get('job_title'))
        ret['disabled'] = _check_user_disabled(request_body.get('disabled'))

        # return a response if any ret values are response objects
        for k, v in ret.items():
            if isinstance(v, Response):
                return v

        return ret

    @staticmethod
    def validate_delete_user_request(user_id: int) -> typing.Union[Response, dict]:
        """ Validates a delete user request body """
        from app.Controllers import UserController

        check_user = _check_user_id(user_id, should_exist=True)
        if isinstance(check_user, Response):
            return check_user

        try:
            org_id = UserController.get_user_by_id(user_id).org_id
        except ValueError as e:
            logger.warning(str(e))
            return g_response("user does not exist", 400)

        return {
            "org_id": org_id
        }

    @staticmethod
    def validate_create_org_request(request_body: dict) -> typing.Union[Response, dict]:
        """ Validates a create org request body """
        org_name = request_body.get('name', request_body.get('org_name'))

        org = _check_org_id(org_name, should_exist=False)
        if isinstance(org, Response):
            return org

        return {
            "org_name": org
        }

    @staticmethod
    def validate_create_task_request(request_body: dict) -> typing.Union[Response, dict]:
        """
        Validates a task request body
        :param request_body:    The request body from the create task request
        :return:                Response if the request body contains invalid values, or the TaskRequest dataclass
        """
        org_id = _check_org_id(request_body.get('org_id', request_body.get('org_name')), should_exist=True)
        if isinstance(org_id, Response):
            return org_id

        ret = {
            'org_id': org_id,
            'type': _check_task_type_id(task_type_id=request_body.get('type_id'), should_exist=True),
            'description': _check_task_description(request_body.get('description')),
            'status': _check_task_status(request_body.get('status'), should_exist=True),
            'time_estimate': _check_task_estimate(request_body.get('time_estimate')),
            'due_time': _check_task_due_time(request_body.get('due_time')),
            'assignee': _check_task_assignee(request_body.get('assignee')),
            'priority': _check_task_priority(request_body.get('priority'))
        }

        # return a response if any ret values are response objects
        for k, v in ret.items():
            if isinstance(v, Response):
                return v

        return ret

    @staticmethod
    def validate_update_task_request(task_id: int, request_body: dict) -> typing.Union[Response, dict]:
        """
        Validates a user request body
        :param task_id:         The task id
        :param request_body:    The request body from the update user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        check_task = _check_task_id(task_id)
        if isinstance(check_task, Response):
            return check_task

        org_id = _check_org_id(request_body.get('org_id', request_body.get('org_name')), should_exist=True)
        if isinstance(org_id, Response):
            return org_id

        ret = {
            'org_id': org_id,
            'type': _check_task_type_id(task_type_id=request_body.get('type_id'), should_exist=True),
            'description': _check_task_description(request_body.get('description')),
            'status': _check_task_status(request_body.get('status'), should_exist=True),
            'time_estimate': _check_task_estimate(request_body.get('time_estimate')),
            'due_time': _check_task_due_time(request_body.get('due_time')),
            'assignee': _check_task_assignee(request_body.get('assignee')),
            'priority': _check_task_priority(request_body.get('priority'))
        }

        # return a response if any ret values are response objects
        for k, v in ret.items():
            if isinstance(v, Response):
                return v

        return ret

    @staticmethod
    def validate_assign_task(request_body: dict) -> typing.Union[Response, dict]:
        """
        Validates the assign task request
        :param request_body:    The request body from the update task request
        :return:                Response if invalid, else a complex dict
        """
        from app.Controllers import TaskController

        task_id = _check_task_id(request_body.get('task_id'))
        if isinstance(task_id, Response):
            return task_id

        assignee = _check_task_assignee(request_body.get('assignee'))
        if isinstance(assignee, Response):
            return assignee

        try:
            org_id = _check_org_id(TaskController.get_task_by_id(task_id).org_id, should_exist=True)
            if isinstance(org_id, Response):
                return org_id
        except ValueError as e:
            logger.warning(str(e))
            return g_response(f"Task with id {task_id} does not exist.", 400)

        return {
            'org_id': org_id,
            'task_id': task_id,
            'assignee': assignee
        }

    @staticmethod
    def validate_drop_task(task_id: int) -> typing.Union[Response, dict]:
        """
        Validates the assign task request
        :param task_id:    The id of the task to drop
        :return:           Response if invalid, else a complex dict
        """
        from app.Controllers import TaskController

        task_id = _check_task_id(task_id)
        if isinstance(task_id, Response):
            return task_id

        org_id = _check_org_id(TaskController.get_task_by_id(task_id).org_id, should_exist=True)
        if isinstance(org_id, Response):
            return org_id

        try:
            assignee = TaskController.get_assignee(task_id)
        except ValueError as e:
            logger.warning(str(e))
            return g_response("Can't drop task because it is not assigned to anyone.")

        return {
            'org_id': org_id,
            'task_id': task_id,
            'assignee': assignee
        }

    @staticmethod
    def validate_transition_task(request_body: dict) -> typing.Union[Response, dict]:
        """ Validates the transition task request """
        from app.Controllers import TaskController

        task_id = _check_task_id(request_body.get('task_id'))
        if isinstance(task_id, Response):
            return task_id

        org_id = _check_org_id(TaskController.get_task_by_id(task_id).org_id, should_exist=True)
        if isinstance(org_id, Response):
            return org_id

        try:
            assignee = TaskController.get_assignee(task_id)
        except ValueError as e:
            logger.warning(str(e))
            assignee = None

        task_status = _check_task_status(request_body.get('task_status'), should_exist=True)
        if isinstance(task_status, Response):
            return task_status

        return {
            'org_id': org_id,
            'task_id': task_id,
            'assignee': assignee,
            'task_status': task_status
        }

    @staticmethod
    def validate_update_user_settings_request(request_body: dict) -> typing.Union[Response, dict]:
        """ Validates updating user settings """
        from app.Controllers import UserController
        from app.Models import UserSetting
        from decimal import Decimal

        user_id = _check_user_id(request_body.pop('user_id'), should_exist=True)
        if isinstance(user_id, Response):
            return user_id

        user_setting_obj = UserSetting(user_id=Decimal(user_id))
        for k, v in request_body.items():
            user_setting_obj.__setattr__(k, v)

        return {
            "org_id": UserController.get_user_by_id(user_id).org_id,
            "user_id": user_id,
            "user_settings": user_setting_obj
        }

    @staticmethod
    def validate_update_org_settings_request(request_body: dict) -> typing.Union[Response, dict]:
        """ Validates updating org settings """
        from app.Models import OrgSetting
        from decimal import Decimal

        org_id = _check_org_id(request_body.pop('org_id'), should_exist=True)
        if isinstance(org_id, Response):
            return org_id

        org_setting_obj = OrgSetting(org_id=Decimal(org_id))
        for k, v in request_body.items():
            org_setting_obj.__setattr__(k, v)

        return {
            "org_id": org_id,
            "org_settings": org_setting_obj
        }

    @staticmethod
    def validate_upsert_task_escalation(escalations: typing.List[dict]) -> typing.Union[typing.List[dict], Response]:
        """ Validates upserting task type escalations """
        valid_escalations = []

        for escalation in escalations:
            task_type_id = _check_task_type_id(escalation.get('task_type_id'), should_exist=True)
            if isinstance(task_type_id, Response):
                return task_type_id

            display_order = _check_escalation_display_order(escalation.get('display_order'))
            if isinstance(display_order, Response):
                return display_order

            ret = {
                "task_type_id": task_type_id,
                "display_order": display_order,
                "delay": _check_escalation_delay(escalation.get('delay')),
                "from_priority": _check_task_priority(escalation.get('from_priority')),
                "to_priority": _check_task_priority(escalation.get('to_priority'))
            }
            # return a response if any ret values are response objects
            for k, v in ret.items():
                if isinstance(v, Response):
                    return v

            with session_scope() as session:
                escalation_exists = session.query(exists().where(
                    and_(
                        TaskTypeEscalation.task_type_id == task_type_id,
                        TaskTypeEscalation.display_order == display_order
                    ))).scalar()

                if escalation_exists:
                    # validate update
                    check_escalation = _check_escalation(
                        task_type_id=task_type_id,
                        display_order=display_order,
                        should_exist=True
                    )
                    if isinstance(check_escalation, Response):
                        return check_escalation
                    ret['action'] = 'update'
                else:
                    # validate create
                    check_escalation = _check_escalation(
                        task_type_id=task_type_id,
                        display_order=display_order,
                        should_exist=False
                    )
                    if isinstance(check_escalation, Response):
                        return check_escalation
                    ret['action'] = 'create'

            valid_escalations.append(ret)

        return valid_escalations
