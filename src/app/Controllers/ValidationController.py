import typing
from app import logger
from app.Controllers import AuthController
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
        logger.debug(f"password length less than {min_length}.")
        return f"Password length less than {min_length}."
    if len([char for char in password if char in special_chars]) < min_special_chars:
        logger.debug(f"password requires more than {min_length} special character(s).")
        return f"Password requires more than {min_length} special character(s)."
    if sum(1 for c in password if c.isupper()) < min_caps:
        logger.debug(f"password requires more than {min_length} capital letter(s).")
        return f"Password requires more than {min_length} capital letter(s)."
    logger.debug(f"password meets requirements")
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
            logger.debug(f"bad email expected str got {type(email)}")
            return Response(f"Bad email expected str got {type(email)}", 400)
        if validate_email(email) is False:
            logger.debug("email is invalid")
            return Response("Invalid email", 400)
        return True

    @staticmethod
    def validate_password(password: str) -> typing.Union[bool, Response]:
        """
        Validates a password. Makes sure it's a string, and can do a strength check.
        :param password:    The password to check
        :return:            True if password is valid, or a Flask Response
        """
        if not isinstance(password, str):
            logger.debug(f"bad email expected str got {type(password)}")
            return Response(f"Bad email expected str got {type(password)}", 400)
        # password_check = _check_password_reqs(password)
        # if isinstance(password_check, str):
        #     return Response(password_check, 400)
        return True

    @staticmethod
    def validate_create_user_request(request_body: dict) -> typing.Union[Response, dataclass]:
        """
        Validates a user request body
        :param request_body:    The request body from the create user request
        :return:                Response if the request body contains invalid values, or the UserRequest dataclass
        """
        from app.Controllers import UserController, OrganisationController

        @dataclass
        class UserRequest:
            """ A user request dataclass which represents the values in a create user request object. """
            org_id: int
            email: str
            password: str
            first_name: str
            last_name: str
            role_name: str

        # check email
        email = request_body.get('email')
        email_check = ValidationController.validate_email(email)
        if isinstance(email_check, Response):
            return email_check
        # check user doesn't already exist
        if UserController.user_exists(request_body.get('email')):
            logger.debug(f"user {request_body.get('email')} already exists")
            return Response(f"User already exists.", 400)
        # check org
        org_identifier = request_body.get('org_id', request_body.get('org_name'))
        if not (isinstance(org_identifier, int) or isinstance(org_identifier, str)):
            logger.debug(f"Bad org_id, expected int|str got {type(org_identifier)}.")
            return Response(f"Bad org_id, expected int|str got {type(org_identifier)}.", 400)
        # check that org exists
        if not OrganisationController.org_exists(org_identifier):
            logger.debug(f"org {org_identifier} doesn't exist")
            return Response(f"Org does not exist", 400)
        # get org_id
        if isinstance(org_identifier, str):
            org_id = OrganisationController.get_org_by_name(org_identifier).id
        elif isinstance(org_identifier, int):
            org_id = org_identifier
        else:
            # should never be here??
            logger.debug("Expected org_id to be set but it isn't.")
            return Response(f"Expected org_id to be set but it isn't.", 400)
        # check password
        password = request_body.get('password')
        password_check = ValidationController.validate_password(password)
        if isinstance(password_check, Response):
            return password_check
        # check firstname
        first_name = request_body.get('first_name')
        if not isinstance(first_name, str):
            logger.debug(f"Bad first_name, expected str got {type(first_name)}.")
            return Response(f"Bad first_name, expected str got {type(first_name)}.", 400)
        if len(first_name) == 0:
            logger.debug(f"first_name is required.")
            return Response(f"first_name is required.", 400)
        # check last_name
        last_name = request_body.get('last_name')
        if not isinstance(last_name, str):
            logger.debug(f"Bad last_name, expected str got {type(last_name)}.")
            return Response(f"Bad last_name, expected str got {type(last_name)}.", 400)
        if len(last_name) == 0:
            logger.debug(f"last_name is required.")
            return Response(f"last_name is required.", 400)
        # check role
        role_name = request_body.get('role_name')
        if not isinstance(role_name, str):
            logger.debug(f"Bad role_name, expected str got {type(role_name)}.")
            return Response(f"Bad role_name, expected str got {type(role_name)}.", 400)
        if len(role_name) == 0:
            logger.debug(f"role_name is required.")
            return Response(f"role_name is required.", 400)
        if not AuthController.role_exists(role_name):
            logger.debug(f"Role {role_name} does not exist")
            return Response(f"Role {role_name} does not exist", 400)

        return UserRequest(
            org_id=org_id,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role_name=role_name
        )

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
            logger.debug(f"organisation {org_name} already exists")
            return Response("Organisation already exists", 400)
        if not isinstance(org_name, str):
            logger.debug(f"bad org_name, exepected str got {type(org_name)}")
            return Response(f"Bad org_name, expected str got {type(org_name)}.", 400)
        if len(org_name) == 0:
            logger.debug(f"org_name is required")
            return Response(f"org_name is required.", 400)

        return OrgRequest(
            org_name=org_name
        )
