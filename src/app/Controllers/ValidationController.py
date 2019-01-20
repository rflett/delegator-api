import typing
from validate_email import validate_email
from flask import Response


def _check_password_reqs(password: str) -> typing.Union[str, bool]:
    """ 
    Ensures a password meets minimum security requirements. 
    
    :param password str: The password to check
    
    :return: A message if it does not meet the requirements, or True
    """
    min_length = 6
    min_special_chars = 1
    min_caps = 1
    special_chars = r' !#$%&\'()*+,-./:;<=>?@[\]^_`{|}~'
    if len(password) < min_length:
        return f"Password length less than {min_length}."
    if len([char for char in password if char in special_chars]) < min_special_chars:
        return f"Password requires more than {min_length} special character(s)."
    if sum(1 for c in password if c.isupper()) < min_caps:
        return f"Password requires more than {min_length} capital letter(s)."
    return True


class ValidationController(object):
    @staticmethod
    def validate_email(email: str) -> typing.Union[bool, Response]:
        """ 
        Validates an email address. It checks to make sure it's a string, and calls the 
        validate_email package which compares it to a huge regex. This package has support
        for MX record check.
        
        :param email str: The email to validate

        :return: True if the email is valid, or a Flask Response.
        """
        if not isinstance(email, str):
            return Response(f"Bad email expected str got {type(email)}", 400)
        if validate_email(email) is False:
            return Response("Invalid email", 400)
        return True

    @staticmethod
    def validate_password(password: str) -> typing.Union[bool, Response]:
        """ 
        Validates a password. Makes sure it's a string, and can do a strength check.

        :param password str: The password to check

        :return: True if password is valid, or a Flask Response
        """
        if not isinstance(password, str):
            return Response(f"Bad email expected str got {type(password)}", 400)
        # password_check = _check_password_reqs(password)
        # if isinstance(password_check, str):
        #     return Response(password_check, 400)
        return True
