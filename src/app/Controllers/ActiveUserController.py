import datetime
import json

from flask import request, Response

from app import session_scope, logger, app, j_response
from app.Models import User, ActiveUser
from app.Models.Enums import Operations, Resources


def _purge_inactive_users() -> None:
    """ Removes users which have been inactive for longer than the threshold. """
    with session_scope() as session:
        inactive_cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=app.config['INACTIVE_USER_TTL'])
        delete_inactive = session.query(ActiveUser).filter(ActiveUser.last_active < inactive_cutoff).delete()
        logger.info(f"purged {delete_inactive} users who have not been active since {inactive_cutoff}")


class ActiveUserController(object):

    @staticmethod
    def user_is_active(user: User) -> None:
        """
        Marks a user as active if they are not active already. If they're already active then update them.
        A cron job should come through and remove active users that have been inactive for the TTL.
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
                logger.debug(f"user {user.id} was not active, but has now been marked as active")
            else:
                # user is active, so update
                already_active.last_active = datetime.datetime.utcnow()
                logger.debug(f"user {user.id} was active, and has been marked as active again")

    @staticmethod
    def user_is_inactive(user: User) -> None:
        """ Mark user as inactive by deleting their record in the active users table """
        with session_scope() as session:
            session.query(ActiveUser).filter(ActiveUser.user_id == user.id).delete()
            logger.debug(f"user {user.id} marked as inactive")

    @staticmethod
    def get_active_users(req: request) -> Response:
        """ Returns all active users for an organisation """
        from app.Controllers import AuthenticationController, AuthorizationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.ACTIVE_USERS
        )

        # remove inactive users
        _purge_inactive_users()

        with session_scope() as session:
            active_users_qry = session.query(ActiveUser).filter(ActiveUser.org_id == req_user.org_id).all()

        active_users = [au.as_dict() for au in active_users_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.ACTIVE_USERS
        )
        logger.debug(f"found {len(active_users)} active users: {json.dumps(active_users)}")
        return j_response(active_users)
