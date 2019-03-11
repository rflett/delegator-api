import typing
from app import logger, g_response
from dataclasses import dataclass
from flask import Response
from validate_email import validate_email


def _check_password_reqs(password: str) -> typing.Union[str, bool]:
    """
    Ensures a password meets minimum security requirements.
    :param password:    The password to check
    :return:            A message if it does not meet the requirements, or True
    """
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
    def validate_create_task_type_request(request_body: dict) -> typing.Union[Response, dataclass]:
        """
        Validates a task type request body
        :param request_body:    The request body from the create task type request
        :return:                Response if the request body contains invalid values, or the TaskTypeRequest dataclass
        """
        from app.Controllers import OrganisationController, TaskController

        @dataclass
        class TaskTypeRequest:
            """ A task type dataclass which represents the values in a create task type object. """
            type: str
            org_id: int

        org_identifier = request_body.get('org_id')
        # check org
        if isinstance(org_identifier, bool):
            return g_response(f"Bad org_id, expected int got {type(org_identifier)}.", 400)
        if not isinstance(org_identifier, int):
            return g_response(f"Bad org_id, expected int got {type(org_identifier)}.", 400)
        # check that org exists
        if not OrganisationController.org_exists(org_identifier):
            logger.info(f"org {org_identifier} doesn't exist")
            return g_response(f"Org does not exist", 400)
        # check type
        task_type = request_body.get('type')
        if not isinstance(request_body.get('type'), str):
            logger.info(f"Bad type, expected str got {type(task_type)}.")
            return g_response(f"Bad type, expected str got {type(task_type)}.", 400)
        if len(task_type) == 0:
            logger.info(f"Task type is required to have length > 0")
            return g_response(f"Task type cannot be empty", 400)
        # check task type doesn't exist already
        if TaskController.task_type_exists(task_type, org_identifier):
            logger.info(f"user {task_type} already exists")
            return g_response(f"Task type already exists.", 400)

        return TaskTypeRequest(
            type=task_type,
            org_id=org_identifier
        )

    @staticmethod
    def validate_create_user_request(request_body: dict, from_signup=False) -> typing.Union[Response, dataclass]:
        """
        Validates a user request body
        :param request_body:    The request body from the create user request
        :param from_signup:     Indicates that this validation request came from the signup page, so
                                we should ignore org and role checks. The organisation won't be created yet, this is
                                pre-creation validation. The role will not be provided because the default role
                                will be given.
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        from app.Controllers import UserController, OrganisationController, AuthController

        @dataclass
        class UserRequest:
            """ A user request dataclass which represents the values in a create user request object. """
            org_id: typing.Optional[int]
            email: str
            password: str
            first_name: str
            last_name: str
            role_name: typing.Optional[str]
            job_title: str

        # check email
        email = request_body.get('email')
        email_check = ValidationController.validate_email(email)
        if isinstance(email_check, Response):
            return email_check
        # check user doesn't already exist
        if UserController.user_exists(request_body.get('email')):
            logger.info(f"user {request_body.get('email')} already exists")
            return g_response(f"User already exists.", 400)
        if not from_signup:
            # check org
            org_identifier = request_body.get('org_id', request_body.get('org_name'))
            if isinstance(org_identifier, bool):
                logger.info(f"Bad org_id, expected int|str got {type(org_identifier)}.")
                return g_response(f"Bad org_id, expected int|str got {type(org_identifier)}.", 400)
            if not isinstance(org_identifier, (int, str)):
                logger.info(f"Bad org_id, expected int|str got {type(org_identifier)}.")
                return g_response(f"Bad org_id, expected int|str got {type(org_identifier)}.", 400)
            # check that org exists
            if not OrganisationController.org_exists(org_identifier):
                logger.info(f"org {org_identifier} doesn't exist")
                return g_response(f"Org does not exist", 400)
            # get org_id
            if isinstance(org_identifier, str):
                org_id = OrganisationController.get_org_by_name(org_identifier).id
            elif isinstance(org_identifier, int):
                org_id = org_identifier
            else:
                # should never be here??
                logger.info("Expected org_id to be set but it isn't.")
                return g_response(f"Expected org_id to be set but it isn't.", 400)
        # check password
        password = request_body.get('password')
        password_check = ValidationController.validate_password(password)
        if isinstance(password_check, Response):
            return password_check
        # check firstname
        first_name = request_body.get('first_name')
        if not isinstance(first_name, str):
            logger.info(f"Bad first_name, expected str got {type(first_name)}.")
            return g_response(f"Bad first_name, expected str got {type(first_name)}.", 400)
        if len(first_name) == 0:
            logger.info(f"first_name is required.")
            return g_response(f"first_name is required.", 400)
        # check last_name
        last_name = request_body.get('last_name')
        if not isinstance(last_name, str):
            logger.info(f"Bad last_name, expected str got {type(last_name)}.")
            return g_response(f"Bad last_name, expected str got {type(last_name)}.", 400)
        if len(last_name) == 0:
            logger.info(f"last_name is required.")
            return g_response(f"last_name is required.", 400)
        # check role
        if not from_signup:
            role_name = request_body.get('role_name')
            if not isinstance(role_name, str):
                logger.info(f"Bad role_name, expected str got {type(role_name)}.")
                return g_response(f"Bad role_name, expected str got {type(role_name)}.", 400)
            if len(role_name) == 0:
                logger.info(f"role_name is required.")
                return g_response(f"role_name is required.", 400)
            if not AuthController.role_exists(role_name):
                logger.info(f"Role {role_name} does not exist")
                return g_response(f"Role {role_name} does not exist", 400)
        job_title = request_body.get('job_title')
        if job_title is not None:
            if not isinstance(job_title, str):
                logger.info(f"Bad job_title, expected str got {type(job_title)}.")
                return g_response(f"Bad job_title, expected str got {type(job_title)}.", 400)
            if len(job_title) == 0:
                logger.info(f"job_title is required.")
                return g_response(f"job_title is required.", 400)

        return UserRequest(
            org_id=None if from_signup else org_id,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role_name=None if from_signup else role_name,
            job_title=job_title
        )

    @staticmethod
    def validate_update_user_request(user_id: int, request_body: dict) -> typing.Union[Response, dataclass]:
        """
        Validates a user request body
        :param request_body:    The request body from the update user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        from app.Controllers import UserController, AuthController, OrganisationController

        @dataclass
        class UserRequest:
            """ A user request dataclass which represents the values in a update user request object. """
            org_id: int
            email: str
            first_name: str
            last_name: str
            role: str
            job_title: str

            def __iter__(self):
                for attr, value in self.__dict__.items():
                    yield attr, value

        # check id
        if not isinstance(user_id, int):
            return g_response(f"Bad identifier, expected int got {type(user_id)}", 400)
        # check user exists
        if not UserController.user_exists(user_id):
            logger.info(f"user {user_id} doesn't exist")
            return g_response(f"User doesn't exist.", 400)
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
        # check org
        org_identifier = request_body.get('org_id', request_body.get('org_name'))
        if isinstance(org_identifier, bool):
            logger.info(f"Bad org_id, expected int|str got {type(org_identifier)}.")
            return g_response(f"Bad org_id, expected int|str got {type(org_identifier)}.", 400)
        if not isinstance(org_identifier, (int, str)):
            logger.info(f"Bad org_id, expected int|str got {type(org_identifier)}.")
            return g_response(f"Bad org_id, expected int|str got {type(org_identifier)}.", 400)
        # check that org exists
        if not OrganisationController.org_exists(org_identifier):
            logger.info(f"org {org_identifier} doesn't exist")
            return g_response(f"Org does not exist", 400)
        # get org_id
        if isinstance(org_identifier, str):
            org_id = OrganisationController.get_org_by_name(org_identifier).id
        elif isinstance(org_identifier, int):
            org_id = org_identifier
        else:
            # should never be here??
            logger.info("Expected org_id to be set but it isn't.")
            return g_response(f"Expected org_id to be set but it isn't.", 400)
        # check firstname
        first_name = request_body.get('first_name')
        if not isinstance(first_name, str):
            logger.info(f"Bad first_name, expected str got {type(first_name)}.")
            return g_response(f"Bad first_name, expected str got {type(first_name)}.", 400)
        if len(first_name) == 0:
            logger.info(f"first_name is required.")
            return g_response(f"first_name is required.", 400)
        # check last_name
        last_name = request_body.get('last_name')
        if not isinstance(last_name, str):
            logger.info(f"Bad last_name, expected str got {type(last_name)}.")
            return g_response(f"Bad last_name, expected str got {type(last_name)}.", 400)
        if len(last_name) == 0:
            logger.info(f"last_name is required.")
            return g_response(f"last_name is required.", 400)
        # check role
        role_name = request_body.get('role_name')
        if not isinstance(role_name, str):
            logger.info(f"Bad role_name, expected str got {type(role_name)}.")
            return g_response(f"Bad role_name, expected str got {type(role_name)}.", 400)
        if len(role_name) == 0:
            logger.info(f"role_name is required.")
            return g_response(f"role_name is required.", 400)
        if not AuthController.role_exists(role_name):
            logger.info(f"Role {role_name} does not exist")
            return g_response(f"Role {role_name} does not exist", 400)
        # check job title
        job_title = request_body.get('job_title')
        if not isinstance(job_title, str):
            logger.info(f"Bad job_title, expected str got {type(job_title)}.")
            return g_response(f"Bad job_title, expected str got {type(job_title)}.", 400)
        if len(job_title) == 0:
            logger.info(f"job_title is required.")
            return g_response(f"job_title is required.", 400)

        return UserRequest(
            org_id=org_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role_name,
            job_title=job_title
        )

    @staticmethod
    def validate_get_user_request(user_id: int) -> typing.Union[Response, int]:
        from app.Controllers import UserController
        # check they exist
        if not UserController.user_exists(user_id):
            logger.info(f"user with id {user_id} does not exist")
            return g_response("User does not exist.", 400)
        return user_id

    @staticmethod
    def validate_create_org_request(request_body: dict) -> typing.Union[Response, dataclass]:
        """
        Validates a user request body

        :param request_body:    The request body from the create org request
        :return:                Response if the request body contains invalid values, or the OrgRequest dataclass
        """
        from app.Controllers import OrganisationController

        @dataclass
        class OrgRequest:
            """ An org request dataclass which represents the values in a create org request object. """
            org_name: str

        # check organisation name
        org_name = request_body.get('name', request_body.get('org_name'))
        if OrganisationController.org_exists(org_name):
            logger.info(f"organisation {org_name} already exists")
            return g_response("Organisation already exists", 400)
        if not isinstance(org_name, str):
            logger.info(f"bad org_name, exepected str got {type(org_name)}")
            return g_response(f"Bad org_name, expected str got {type(org_name)}.", 400)
        if len(org_name) == 0:
            logger.info(f"org_name is required")
            return g_response(f"org_name is required.", 400)

        return OrgRequest(
            org_name=org_name
        )
