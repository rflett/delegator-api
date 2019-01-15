import typing
from validate_email import validate_email
from flask import Response


def _check_password_reqs(password: str) -> typing.Union[str, bool]:
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
    def validate_email(email: str) -> typing.Union[None, Response]:
        """ Validates an email """
        if not isinstance(email, str):
            return Response(f"Bad email expected str got {type(email)}", 400)
        if validate_email(email) is False:
            return Response("Invalid email", 400)
        return None

    @staticmethod
    def validate_password(password: str) -> typing.Union[None, Response]:
        """ Validates a password """
        if not isinstance(password, str):
            return Response(f"Bad email expected str got {type(password)}", 400)
        return None
