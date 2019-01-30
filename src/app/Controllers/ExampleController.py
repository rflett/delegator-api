from app.Controllers import AuthController
from app.Models.RBAC import Operation, Resource
from flask import request, Response


class ExampleController(object):
    @staticmethod
    def example(req: request) -> Response:
        """
        An example.

        :param req request: The Flask request object.

        :return: Flask Response
        """
        user = AuthController.get_user_from_request(req)
        if isinstance(user, Response):
            return user
        else:
            if user.can(Operation.CREATE, Resource.TASK):
                #################
                # DO YOUR THANG #
                #################
                user.log(Operation.CREATE, Resource.TASK)
                return Response("That's the example done.")
            else:
                return Response(f"No permissions to {Operation.CREATE} {Resource.TASK}", 403)
