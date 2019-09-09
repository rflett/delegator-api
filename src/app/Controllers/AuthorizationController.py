import json
import random
import string
import typing

from flask import request

from app import logger, g_response, session_scope
from app.Controllers import ValidationController
from app.Exceptions import AuthorizationError
from app.Models import User
from app.Models.Enums import ResourceScopes


class AuthorizationController(object):
    @staticmethod
    def authorize_request(
            auth_user: User,
            operation: str,
            resource: str,
            affected_user_id: typing.Union[int, None] = None
    ) -> None:
        """ Check to see if a user is authorized to perform an action

        :param auth_user:           The user to authorize
        :param operation:           The operation to perform
        :param resource:            The resource affected
        :param affected_user_id:    If the resource is a user, their user_id
        :return:
        """
        from app.Controllers import UserController

        # mark user as active
        auth_user.is_active()

        # check users scope
        user_permission_scope = auth_user.can(operation, resource)

        # no user scope
        if user_permission_scope is False:
            logger.info(f"User {auth_user.id} cannot perform {operation} on {resource}.")
            raise AuthorizationError(f"No permissions to {operation} {resource}.")

        # scope of self - they can do things against this resource if they own it
        if user_permission_scope == ResourceScopes.SELF:
            if auth_user.id != affected_user_id:
                msg = f"User id {auth_user.id} cannot perform {operation} on {resource} because their scope " \
                    f"is {user_permission_scope} but the affected user is {affected_user_id}."
                logger.info(msg)
                raise AuthorizationError(msg)

        # scope of org - they can do things against this resource as long as it's in the same org
        elif user_permission_scope == ResourceScopes.ORG:
            if affected_user_id is not None:
                # get the affected user's org_id
                affected_user_org_id = UserController.get_user_by_id(affected_user_id).org_id
                if auth_user.org_id != affected_user_org_id:
                    msg = f"User id {auth_user.id} cannot perform {operation} on {resource} because their scope " \
                        f"is {user_permission_scope} but the affected user is {affected_user_id} which is " \
                        f"in org {affected_user_org_id}"
                    logger.info(msg)
                    raise AuthorizationError(msg)

    @staticmethod
    def reset_password(req: request):
        """ TODO remove and make it an email based reset. """
        from app.Controllers import UserController
        request_body = req.get_json()
        ValidationController.validate_email(request_body.get('email'))

        with session_scope():
            logger.info(f"received password reset for {request_body.get('email')}")
            user = UserController.get_user_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            logger.info(json.dumps(user.as_dict()))
            logger.info(f"password successfully reset for {request_body.get('email')}")
            return g_response(f"Password reset successfully, new password is {new_password}")
