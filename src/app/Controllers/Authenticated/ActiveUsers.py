import datetime

from flask import current_app
from flask_restx import Namespace, fields

from app.Extensions.Database import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import authorize, requires_jwt
from app.Models.Dao import ActiveUser
from app.Models.Enums import Operations, Resources

api = Namespace(path="/active-users", name="Active Users", description="Get the recently active users")
active_user_dto = api.model(
    "ActiveUser",
    {
        "user_id": fields.Integer(),
        "org_id": fields.Integer(),
        "first_name": fields.String(),
        "last_name": fields.String(),
        "last_active": fields.String(),
    },
)
response = api.model("ActiveUsers", {"active_users": fields.List(fields.Nested(active_user_dto))})


@api.route("/")
class ActiveUsers(RequestValidationController):
    @requires_jwt
    @authorize(Operations.GET, Resources.ACTIVE_USERS)
    @api.marshal_with(response, code=200)
    def get(self, **kwargs):
        """Returns all active users in the organisation"""
        req_user = kwargs["req_user"]

        # remove inactive users
        self._purge_inactive_users()

        # query db for active users
        with session_scope() as session:
            active_users_qry = session.query(ActiveUser).filter_by(org_id=req_user.org_id).all()

        # convert to list of active user dicts
        active_users = [au.as_dict() for au in active_users_qry]
        req_user.log(operation=Operations.GET, resource=Resources.ACTIVE_USERS)
        current_app.logger.debug(f"Found {len(active_users)} active users.")
        return {"active_users": active_users}, 200

    @staticmethod
    def _purge_inactive_users() -> None:
        """ Removes users from the active users table which have been inactive for longer than the TTL. """
        with session_scope() as session:
            inactive_cutoff = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=current_app.config["INACTIVE_USER_TTL"]
            )
            delete_inactive = session.query(ActiveUser).filter(ActiveUser.last_active < inactive_cutoff).delete()
            current_app.logger.info(f"Purged {delete_inactive} users who have not been active for {inactive_cutoff}s.")
