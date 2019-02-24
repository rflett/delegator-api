import datetime
import typing
from app import session_scope, logger, g_response
from app.Controllers import AuthController
from app.Models import User, ActiveUser
from flask import request, Response


def _get_user_from_request(req: request) -> typing.Union[User, Response]:
    """
    Get the user object that is claimed in the JWT payload.
    :param req: The Flask request
    :return:    A User object if a user is found, or a Flask Response
    """
    from app.Controllers import UserController

    # get auth from request
    auth = req.headers.get('Authorization', None)
    payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))

    # get user id
    if isinstance(payload, dict):
        user_id = payload.get('claims').get('user_id')
        logger.info(f"found user id {user_id} in the request JWT")
    else:
        logger.info("missing payload from the bearer token")
        return g_response("Missing payload from Bearer token", 401)

    # get User object
    try:
        user = UserController.get_user_by_id(user_id)
        return user
    except Exception as e:
        logger.error(str(e))
        return g_response('No user found in Bearer token.', 401)


class ActiveUserController(object):

    @staticmethod
    def user_is_active(user: typing.Optional[User], request: typing.Optional[request]) -> typing.Optional[Response]:
        """
        Marks a user as active if they are not active already. If they're already active then update them.
        A cron job should come through and remove active users that have
        :param user:
        :param request:
        :return: Response or None
        """
        if user is None:
            if request is not None:
                user = _get_user_from_request(request)
                if isinstance(user, Response):
                    return user
            else:
                # request and user are none so..
                return g_response("missing both user and request, require at least one", 400)

        with session_scope() as session:
            already_active = session.query(ActiveUser).filter(ActiveUser.user_id == user.id).first()
            if already_active is None:
                # user is not active, so create
                active_user = ActiveUser(
                    user_id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    last_active=datetime.datetime.utcnow()
                )
                session.add(active_user)
            else:
                # user is active, so update
                already_active.last_active = datetime.datetime.utcnow()
            return g_response(status=204)

    @staticmethod
    def user_is_inactive(user: typing.Optional[User], request: typing.Optional[request]) -> typing.Optional[Response]:
        """
        Mark user as inactive by deleting their record in the active users table
        :param user:
        :param request:
        :return: Response or None
        """
        if user is None:
            if request is not None:
                user = _get_user_from_request(request)
                if isinstance(user, Response):
                    return user
            else:
                # request and user are none so..
                return g_response("missing both user and request, require at least one", 400)

        with session_scope() as session:
            session.query(ActiveUser).filter(ActiveUser.user_id == user.id).delete()
