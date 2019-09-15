import datetime

from flask import Response
from flask_restplus import Namespace, fields

from app import session_scope, logger, app
from app.Decorators import authorize, requires_jwt, handle_exceptions
from app.Controllers.Base import RequestValidationController
from app.Models import ActiveUser
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
    @requires_jwt
    @handle_exceptions
    @authorize(Operations.GET, Resources.ACTIVE_USERS)
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

    @staticmethod
    def _purge_inactive_users() -> None:
        """ Removes users from the active users table which have been inactive for longer than the TTL. """
        with session_scope() as session:
            inactive_cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=app.config['INACTIVE_USER_TTL'])
            delete_inactive = session.query(ActiveUser).filter(ActiveUser.last_active < inactive_cutoff).delete()
            logger.info(f"Purged {delete_inactive} users who have not been active for {inactive_cutoff}s.")
