import datetime

from flask import Response
from flask_restplus import Namespace, fields

from app import session_scope, logger, app
from app.Controllers.Base import RequestValidationController
from app.Models import User, ActiveUser
from app.Models.Enums import Operations, Resources

active_user_route = Namespace(
    path="/active-users",
    name="Active Users",
    description="Get the recently active users"
)

active_user_model = active_user_route.model('ActiveUser', {
    "user_id": fields.Integer,
    "org_id": fields.Integer,
    "first_name": fields.String,
    "last_name": fields.String,
    "last_active": fields.String
})

active_users_model = active_user_route.model('ActiveUsers', {
    'active_users': fields.List(fields.Nested(active_user_model))
})


@active_user_route.route("/")
class ActiveUserController(RequestValidationController):
    @staticmethod
    def _purge_inactive_users() -> None:
        """ Removes users from the active users table which have been inactive for longer than the TTL. """
        with session_scope() as session:
            inactive_cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=app.config['INACTIVE_USER_TTL'])
            delete_inactive = session.query(ActiveUser).filter(ActiveUser.last_active < inactive_cutoff).delete()
            logger.info(f"Purged {delete_inactive} users who have not been active for {inactive_cutoff}s.")

    @staticmethod
    def user_is_active(user: User) -> None:
        """Marks a user as active if they are not active already. If they're already active then update them.

        :param user: The user to mark as active
        :return:
        """
        with session_scope() as session:
            already_active = session.query(ActiveUser).filter_by(user_id=user.id).first()
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

    @staticmethod
    def user_is_inactive(user: User) -> None:
        """Mark user as inactive by deleting their record in the active users table

        :param user: The user to mark as inactive
        :return:
        """
        with session_scope() as session:
            session.query(ActiveUser).filter_by(user_id=user.id).delete()

    @active_user_route.doc("Returns all active users in the organisation")
    @active_user_route.response(200, "Success", active_users_model)
    def get(self, **kwargs) -> Response:
        req_user = kwargs['req_user']

        # remove inactive users
        self._purge_inactive_users()

        # query db for active users
        with session_scope() as session:
            active_users_qry = session.query(ActiveUser).filter_by(org_id=req_user.org_id).all()

        # convert to list of active user dicts
        active_users = [au.as_dict() for au in active_users_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.ACTIVE_USERS
        )
        logger.debug(f"Found {len(active_users)} active users.")
        return self.ok({"active_users": active_users})
