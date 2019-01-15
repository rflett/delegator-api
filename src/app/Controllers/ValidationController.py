import typing
from validate_email import validate_email
from flask import Response


class ValidationController(object):

    @staticmethod
    def validate_email(email: str) -> typing.Union[None, Response]:
        if email is None:
            return Response("Email missing", 400)
        if validate_email(email) is False or type(email) != str:
            return Response("Email invalid", 400)
        return None

    @staticmethod
    def validate_password(password: str) -> typing.Union[None, Response]:
        if not isinstance(password, str) or password is None:
            return Response("Invalid password", 400)
        return None
