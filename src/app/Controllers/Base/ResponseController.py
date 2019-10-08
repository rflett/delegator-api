import json
import typing

from flask import Response
from flask_restplus import Resource


class ResponseController(Resource):
    @staticmethod
    def ok(body: typing.Optional[typing.Union[dict, list, str]]) -> Response:
        """Returns an ok json response"""
        if isinstance(body, str):
            data = {"msg": body}
        else:
            data = body

        return Response(
            json.dumps(data),
            status=200,
            headers={'Content-Type': 'application/json'}
        )

    @staticmethod
    def created(body: typing.Optional[typing.Union[dict, list, str]]) -> Response:
        """Returns a created json response"""
        if isinstance(body, str):
            data = {"msg": body}
        else:
            data = body

        return Response(
            json.dumps(data),
            status=201,
            headers={'Content-Type': 'application/json'}
        )

    @staticmethod
    def no_content() -> Response:
        """Returns a no content response"""
        return Response(
            status=204,
            headers={'Content-Type': 'application/json'}
        )

    @staticmethod
    def unprocessable(body: typing.Optional[typing.Union[dict, list, str]]) -> Response:
        """Returns a unprocessable response"""
        if isinstance(body, str):
            data = {"msg": body}
        else:
            data = body

        return Response(
            json.dumps(data),
            status=422,
            headers={'Content-Type': 'application/json'}
        )
