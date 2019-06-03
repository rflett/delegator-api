import json
import random
import string
import typing
from app import logger, g_response, session_scope
from app.Controllers import ValidationController
from app.Models import User
from app.Models.RBAC import ResourceScope
from flask import Response, request


def _authorize_self(
        auth_user: User,
        user_permission_scope: str,
        operation: str,
        resource: str,
        resource_user_id: int,
        resource_org_id: int
) -> typing.Union[bool, Response]:
    """ This user can only perform actions on resources it owns """
    if resource_user_id is not None and resource_org_id is not None:
        # check ids match
        if auth_user.id == resource_user_id and auth_user.org_id == resource_org_id:
            logger.info(f"user {auth_user.id} has {user_permission_scope} permissions, "
                        f"and can {operation} {resource}")
            return True
        else:

            # they don't own this resource
            logger.info(f"No permissions to {operation} {resource}, "
                        f"because user {auth_user.id} != resource_user_id {resource_user_id} "
                        f"or user's org {auth_user.org_id} != resource_org_id {resource_org_id}")
            return g_response(f"No permissions to {operation} {resource}, "
                              f"because user {auth_user.id} does not own it.", 403)
    else:
        logger.warning(f"resource_org_id is None, resource_user_id is None")
        return g_response("resource_org_id is None, resource_user_id is None", 403)


def _authorize_org(
        auth_user: User,
        user_permission_scope: str,
        operation: str,
        resource: str,
        resource_user_id: int,
        resource_org_id: int
) -> typing.Union[bool, Response]:
    """ this user can perform operations on resources in its organisation """
    from app.Controllers import UserController

    if resource_org_id is not None:
        # check org id matches
        if auth_user.org_id == resource_org_id:
            # optionally check resource_user_id is in same org
            if resource_user_id is not None:
                resource_user = UserController.get_user_by_id(resource_user_id)
                if auth_user.org_id != resource_user.org_id:
                    logger.info(f"No permissions to {operation} {resource}, "
                                f"because {auth_user.org_id} != {resource_user.org_id} "
                                f"however, {auth_user.org_id} == {resource_org_id}")
                    return g_response(f"No permissions to {operation} {resource}, "
                                      f"because user {auth_user.id} is not "
                                      f"in the same org as the resource user id {resource_user_id} which "
                                      f"is in org {resource_user.org_id}", 403)

            logger.info(f"user {auth_user.id} has {user_permission_scope} permissions, "
                        f"and can {operation} {resource}")
            return True
        else:
            # this resource belongs to a different organisation
            logger.info(f"No permissions to {operation} {resource}, because "
                        f"user's org {auth_user.org_id} != resource_org_id {resource_org_id}")
            return g_response(f"No permissions to {operation} {resource}, "
                              f"because user {auth_user.id} is in org {auth_user.org_id} but "
                              f"the resource belongs to org {resource_org_id}.", 403)
    else:
        return g_response("resource_org_id is None", 403)


class AuthController(object):
    """
    The AuthController manages functions regarding generating, decoding and validating
    JWT tokens, login/logout functionality, and validating Authorization headers.
    """
    @staticmethod
    def authorize_request(
            auth_user: User,
            operation: str,
            resource: str,
            resource_org_id: typing.Optional[int] = None,
            resource_user_id: typing.Optional[int] = None
    ) -> typing.Union[Response, bool]:
        """
        Checks to see if the user in the request has authorization to perform the request operation on a
        particular resource.
        :param auth_user:           The user to authorize
        :param operation:           The operation to perform
        :param resource:            The resource to affect
        :param resource_org_id:     If the resource has an org_id, this is it
        :param resource_user_id:    If the resource has a user_id, this is it
        :return:                    The User object if they have authority, or a Response if the don't
        """
        # mark user as active
        auth_user.is_active()

        # deal with permissions
        user_permission_scope = auth_user.can(operation, resource)
        if user_permission_scope is False:
            logger.info(f"user id {auth_user.id} cannot perform {operation} on {resource}")
            return g_response(f"No permissions to {operation} {resource}", 403)

        # TODO this is now the same, so no need to compare scopes, just pass it to the function.
        elif user_permission_scope == ResourceScope.SELF:
            # this user can only perform actions on resources it owns
            return _authorize_self(
                auth_user=auth_user,
                user_permission_scope=user_permission_scope,
                operation=operation,
                resource=resource,
                resource_user_id=resource_user_id,
                resource_org_id=resource_org_id
            )

        elif user_permission_scope == ResourceScope.ORG:
            # this user can perform operations on resources in its organisation
            return _authorize_org(
                auth_user=auth_user,
                user_permission_scope=user_permission_scope,
                operation=operation,
                resource=resource,
                resource_user_id=resource_user_id,
                resource_org_id=resource_org_id
            )

        elif user_permission_scope == ResourceScope.GLOBAL:
            # admin OR scope doesn't apply for this permission since the check is done elsewhere
            logger.info(f"user {auth_user.id} has {user_permission_scope} permissions "
                        f"for {operation} {resource}")
            return True

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
