import datetime
import pytz

import structlog
from flask import request, current_app
from flask_restx import Namespace, fields
from sqlalchemy import and_
from sqlalchemy.orm import aliased

from app.Extensions.Database import session_scope
from app.Extensions.Errors import AuthorizationError
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Models import Event, Email, Subscription
from app.Models.Dao import User, UserPasswordToken, ActiveUser
from app.Models.Enums import Operations, Resources, Events, Roles
from app.Models.RBAC import Role

api = Namespace(path="/users", name="Users", description="Manage a user or users")
log = structlog.getLogger()


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


class NullableInteger(fields.Integer):
    __schema_type__ = ["integer", "null"]
    __schema_example__ = "nullable string"


@api.route("/minimal")
class MinimalUsers(RequestValidationController):
    min_user_response = api.model(
        "Minimal User Response",
        {
            "id": fields.Integer(),
            "uuid": fields.String(),
            "email": fields.String(),
            "first_name": fields.String(),
            "last_name": fields.String(),
            "job_title": fields.String(),
        },
    )
    get_min_users_response = api.model(
        "Get Minimal Users Response", {"users": fields.List(fields.Nested(min_user_response))}
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.USERS)
    @api.marshal_with(get_min_users_response, code=200)
    def get(self, **kwargs):
        """Get all users with minimal dto"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            users_qry = (
                session.query(User.id, User.uuid, User.email, User.first_name, User.last_name, User.job_title)
                .filter(and_(User.org_id == req_user.org_id, User.deleted == None))  # noqa
                .all()
            )

        users = []

        for user in users_qry:
            id_, uuid_, email, first_name, last_name, job_title = user
            users.append(
                {
                    "id": id_,
                    "uuid": uuid_,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "job_title": job_title,
                }
            )

        req_user.log(Operations.GET, Resources.USERS)
        return {"users": users}, 200


@api.route("/")
class UserController(RequestValidationController):
    role_dto = api.model(
        "Get Users Role",
        {
            "id": fields.String(enum=Roles.all),
            "rank": fields.Integer(min=0, max=2),
            "name": fields.String(enum=["Administrator", "Delegator", "Team Member", "Locked Account"]),
            "description": fields.String(),
        },
    )
    user_response = api.model(
        "User Response",
        {
            "id": fields.Integer,
            "uuid": fields.String(),
            "org_id": fields.Integer,
            "email": fields.String,
            "first_name": fields.String,
            "last_name": fields.String,
            "role": fields.Nested(role_dto),
            "role_before_locked": fields.String(),
            "disabled": NullableDateTime,
            "job_title": fields.String,
            "deleted": NullableDateTime,
            "created_at": fields.String,
            "created_by": fields.String,
            "updated_at": NullableDateTime,
            "updated_by": fields.String(),
            "last_active": fields.String(),
            "invite_accepted": fields.Boolean,
            "invite_expires_in": NullableInteger,
        },
    )
    get_users_response = api.model("Get Users Response", {"users": fields.List(fields.Nested(user_response))})

    @requires_jwt
    @authorize(Operations.GET, Resources.USERS)
    @api.marshal_with(get_users_response, code=200)
    def get(self, **kwargs):
        """Get all users """
        req_user = kwargs["req_user"]

        # query for all users in the requesting user's organisation
        with session_scope() as session:
            this_user, created_by, updated_by = aliased(User), aliased(User), aliased(User)
            users_qry = (
                session.query(
                    this_user,
                    Role,
                    created_by.first_name,
                    created_by.last_name,
                    updated_by.first_name,
                    updated_by.last_name,
                    ActiveUser.last_active,
                )
                .join(Role, Role.id == this_user.role)
                .join(created_by, created_by.id == this_user.created_by)
                .outerjoin(updated_by, updated_by.id == this_user.updated_by)
                .outerjoin(ActiveUser, ActiveUser.user_id == this_user.id)
                .filter(and_(this_user.org_id == req_user.org_id, this_user.deleted == None))  # noqa
                .all()
            )

        users = []

        for user in users_qry:
            (user_, role, created_by_fn, created_by_ln, updated_by_fn, updated_by_ln, last_active) = user

            created_by = created_by_fn + " " + created_by_ln

            if updated_by_fn is not None and updated_by_ln is not None:
                updated_by = updated_by_fn + " " + updated_by_ln
            else:
                updated_by = None

            if last_active is not None:
                last_active = pytz.utc.localize(last_active)
                last_active = last_active.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

            user_dict = user_.as_dict()
            user_dict["created_by"] = created_by
            user_dict["updated_by"] = updated_by
            user_dict["last_active"] = last_active
            user_dict["role"] = role.as_dict()

            users.append(user_dict)

        log.info(f"found {len(users)} users.")
        req_user.log(Operations.GET, Resources.USERS)
        return {"users": users}, 200

    create_user_request = api.model(
        "Create User Request",
        {
            "email": fields.String(required=True),
            "role_id": fields.String(enum=["ORG_ADMIN", "DELEGATOR", "USER"], required=True),
            "first_name": fields.String(required=True),
            "last_name": fields.String(required=True),
            "job_title": fields.String(),
        },
    )

    @requires_jwt
    @authorize(Operations.CREATE, Resources.USER)
    @api.expect(create_user_request, validate=True)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Create a user"""
        request_body = request.get_json()
        req_user = kwargs["req_user"]

        # validate user
        email = request_body["email"]
        self.validate_email(email)
        self.check_user_id(email, should_exist=False)
        self.check_user_role(req_user, request_body["role_id"])

        with session_scope() as session:
            user = User(
                org_id=req_user.org_id,
                email=request_body["email"],
                first_name=request_body["first_name"],
                last_name=request_body["last_name"],
                role=request_body["role_id"],
                job_title=request_body.get("job_title"),
                created_by=req_user.id,
            )
            session.add(user)

        with session_scope() as session:
            password_token = UserPasswordToken(user.id)
            session.add(password_token)

        # create user settings
        user.create_settings()
        user.reset_avatar(first_time=True)

        # send welcome email
        email = Email(user.email)
        email.send_welcome_new_user(
            first_name=user.first_name,
            link=current_app.config["PUBLIC_WEB_URL"] + "/account-setup?token=" + password_token.token,
            inviter=req_user,
        )

        req_user.log(Operations.CREATE, Resources.USER, resource_id=user.id)

        Event(
            org_id=user.org_id,
            event=Events.user_created,
            event_id=user.id,
            event_friendly=f"Created by {req_user.name()}.",
        ).publish()

        Event(
            org_id=req_user.org_id,
            event=Events.user_created_user,
            event_id=req_user.id,
            event_friendly=f"Created {user.name()}.",
        ).publish()
        log.info(f"User {req_user.id} created user {user.id}")

        # increment chargebee subscription plan_quantity
        subscription = Subscription(user.orgs.chargebee_subscription_id)
        subscription.increment_subscription(req_user)

        return "", 204

    update_user_request = api.model(
        "Update User Request",
        {
            "id": fields.Integer(required=True),
            "email": fields.String(required=True),
            "role_id": fields.String(enum=["ORG_ADMIN", "DELEGATOR", "USER"], required=True),
            "first_name": fields.String(required=True),
            "last_name": fields.String(required=True),
            "job_title": fields.String(),
        },
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @api.expect(update_user_request, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Update a user. """
        req_user: User = kwargs["req_user"]
        request_body = request.get_json()

        user_to_update = self.check_user_id(request_body["id"], should_exist=True)
        self.check_auth_scope(user_to_update, **kwargs)
        self.check_user_role(req_user, request_body["role_id"], user_to_update)

        if user_to_update.email != request_body["email"]:
            # only admins can update emails of other users
            if req_user.role != Roles.ORG_ADMIN:
                raise AuthorizationError("Only an organisation administrator can update a user email")
            # org admin email cannot be changed yet without Delegator assistance
            if user_to_update.role == Roles.ORG_ADMIN:
                raise AuthorizationError("Please contact us to change the administrators email address")

            self.validate_email(request_body["email"])
            with session_scope():
                user_to_update.email = request_body["email"]

        with session_scope():
            user_to_update.role = request_body["role_id"]
            user_to_update.first_name = request_body["first_name"]
            user_to_update.last_name = request_body["last_name"]
            user_to_update.job_title = request_body.get("job_title")
            user_to_update.updated_at = datetime.datetime.utcnow()
            user_to_update.updated_by = req_user.id

        Event(
            org_id=user_to_update.org_id,
            event=Events.user_updated,
            event_id=user_to_update.id,
            event_friendly=f"Updated by {req_user.name()}",
        ).publish()
        Event(
            org_id=req_user.org_id,
            event=Events.user_updated_user,
            event_id=req_user.id,
            event_friendly=f"Updated {user_to_update.name()}.",
        ).publish()
        req_user.log(Operations.UPDATE, Resources.USER, resource_id=user_to_update.id)
        log.info(f"User {req_user.id} updated user {user_to_update.id}")
        return "", 204
