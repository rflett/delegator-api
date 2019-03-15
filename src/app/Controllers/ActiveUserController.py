import datetime
import json
import typing
from app import session_scope, logger, g_response, app, j_response
from app.Controllers import AuthController
from app.Models import User, ActiveUser
from app.Models.RBAC import Operation, Resource
from flask import request, Response


def _purge_inactive_users() -> None:
    """
    Removes users which have been inactive for longer than the threshold.
    :return: None
    """
    with session_scope() as session:
        inactive_cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=app.config['INACTIVE_USER_TTL'])
        delete_inactive = session.query(ActiveUser).filter(ActiveUser.last_active < inactive_cutoff).delete()
        logger.info(f"purged {delete_inactive} users who have not been active since {inactive_cutoff}")


def _get_user_from_request(req: request) -> typing.Union[User, Response]:
    """
    Get the user object that is claimed in the JWT payload.
    :param req: The Flask request
    :return:    A User object if a user is found, or a Flask Response
    """
    from app.Controllers import UserController

    # get auth from request
    auth = req.headers.get('Authorization', None)
    if auth is None:
        return g_response("Missing Authorization header")

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
    def user_is_active(user: User) -> Response:
        """
        Marks a user as active if they are not active already. If they're already active then update them.
        A cron job should come through and remove active users that have
        :param user:
        :return: Response or None
        """
        with session_scope() as session:
            already_active = session.query(ActiveUser).filter(ActiveUser.user_id == user.id).first()
            if already_active is None:
                # user is not active, so create
                active_user = ActiveUser(
                    user_id=user.id,
                    org_id=user.org_id,
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
    def user_is_inactive(user: User) -> Response:
        """
        Mark user as inactive by deleting their record in the active users table
        :param user:
        :return: Response or None
        """
        with session_scope() as session:
            session.query(ActiveUser).filter(ActiveUser.user_id == user.id).delete()

        return g_response(status=204)

    @staticmethod
    def get_active_users() -> Response:
        """
        Returns all active users for an organisation
        :return: Active users
        """
        from app.Controllers import AuthController

        req_user = AuthController.authorize_request(
            request_headers=request.headers,
            operation=Operation.GET,
            resource=Resource.ACTIVE_USERS
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            # remove inactive users
            _purge_inactive_users()

            with session_scope() as session:
                active_users_qry = session.query(ActiveUser).filter(ActiveUser.org_id == req_user.org_id).all()

            active_users = [au.as_dict() for au in active_users_qry]

            logger.info(f"retrieved {len(active_users)} active users: {json.dumps(active_users)}")
            return j_response(active_users)
