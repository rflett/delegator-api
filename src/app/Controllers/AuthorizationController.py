import json
import random
import string
import typing
from app import logger, g_response, session_scope
from app.Controllers import ValidationController
from app.Exceptions import AuthorizationError
from app.Models import User
from app.Models.Enums import ResourceScopes
from flask import Response, request


class AuthorizationController(object):
    @staticmethod
    def authorize_request(
            auth_user: User,
            operation: str,
            resource: str,
            affected_user_id: typing.Union[int, None] = None
    ) -> None:
        """
        Checks to see if the user in the request has authorization to perform the request operation on a
        particular resource.
        :param auth_user:           The user to authorize
        :param operation:           The operation to perform
        :param resource:            The resource to affect
        :param affected_user_id:
        :raises:                    AuthorizationError if the user is unauthorized
        """
        from app.Controllers import UserController

        # mark user as active
        auth_user.is_active()

        # check users scope
        user_permission_scope = auth_user.can(operation, resource)
        if user_permission_scope is False:
            logger.info(f"user id {auth_user.id} cannot perform {operation} on {resource}")
            raise AuthorizationError(f"No permissions to {operation} {resource}")

        if user_permission_scope == ResourceScopes.SELF:
            if auth_user.id != affected_user_id:
                msg = f"user id {auth_user.id} cannot perform {operation} on {resource} because their scope " \
                    f"is {user_permission_scope} but the affected user is {affected_user_id}"
                logger.info(msg)
                raise AuthorizationError(msg)
        elif user_permission_scope == ResourceScopes.ORG:
            if affected_user_id is not None:
                try:
                    affected_user_org_id = UserController.get_user_by_id(affected_user_id).org_id
                except ValueError as e:
                    raise AuthorizationError(e)
                if auth_user.org_id != affected_user_org_id:
                    msg = f"user id {auth_user.id} cannot perform {operation} on {resource} because their scope " \
                        f"is {user_permission_scope} but the affected user is {affected_user_id} which is " \
                        f"in org {affected_user_org_id}"
                    logger.info(msg)
                    raise AuthorizationError(msg)

    @staticmethod
    def reset_password(req: request):
        from app.Controllers import UserController
        request_body = req.get_json()
        check_email = ValidationController.validate_email(request_body.get('email'))
        # invalid
        if isinstance(check_email, Response):
            return check_email

        with session_scope():
            logger.info(f"received password reset for {request_body.get('email')}")
            user = UserController.get_user_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            logger.info(json.dumps(user.as_dict()))
            logger.info(f"password successfully reset for {request_body.get('email')}")
            return g_response(f"Password reset successfully, new password is {new_password}")
