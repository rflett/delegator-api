import datetime

from flask import Response, request
from flask_restplus import Namespace
from sqlalchemy import and_
from sqlalchemy.orm import aliased

from app import session_scope, subscription_api, logger, email_api, app
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Exceptions import ProductTierLimitError, ValidationError
from app.Models import User, Activity, Task, UserPasswordToken, Subscription
from app.Models.Enums import Operations, Resources, Events
from app.Models.RBAC import Role
from app.Models.Request import create_user_request, update_user_request
from app.Models.Response import message_response_dto, user_response, get_users_response
from app.Services import UserService

users_route = Namespace(path="/users", name="Users", description="Manage a user or users")

user_service = UserService()


@users_route.route("/")
class UserController(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.USERS)
    @users_route.response(200, "Users retrieved", get_users_response)
    @users_route.response(400, "Bad request", message_response_dto)
    @users_route.response(403, "Insufficient privileges", message_response_dto)
    def get(self, **kwargs) -> Response:
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
                    updated_by.last_name
                )
                .join(Role, Role.id == this_user.role)
                .join(created_by, created_by.id == this_user.created_by)
                .outerjoin(updated_by, updated_by.id == this_user.updated_by)
                .filter(
                    and_(
                        this_user.org_id == req_user.org_id,
                        Role.rank >= req_user.roles.rank,
                        this_user.deleted == None  # noqa
                    )
                )
                .all()
            )

        users = []

        for user in users_qry:
            (
                user_,
                role,
                created_by_fn,
                created_by_ln,
                updated_by_fn,
                updated_by_ln
            ) = user

            created_by = created_by_fn + " " + created_by_ln

            if updated_by_fn is not None and updated_by_ln is not None:
                updated_by = updated_by_fn + " " + created_by_ln
            else:
                updated_by = None

            user_dict = user_.as_dict()
            user_dict["created_by"] = created_by
            user_dict["updated_by"] = updated_by
            user_dict["role"] = role.as_dict()

            users.append(user_dict)

        logger.info(f"found {len(users)} users.")
        req_user.log(operation=Operations.GET, resource=Resources.USERS)
        return self.ok({"users": users})

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.CREATE, Resources.USER)
    @users_route.expect(create_user_request)
    @users_route.response(200, "Successfully created user", user_response)
    @users_route.response(400, "Bad request", message_response_dto)
    @users_route.response(402, "Subscription limit reached", message_response_dto)
    @users_route.response(403, "Insufficient privileges", message_response_dto)
    @users_route.response(404, "User does not exist", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Create a user"""
        request_body = request.get_json()

        req_user = kwargs["req_user"]

        # validate user
        self.validate_create_user_request(req_user, request_body)

        # Check that the user hasn't surpassed limits on their product tier
        with session_scope() as session:
            existing_user_count = session.query(User).filter_by(org_id=req_user.org_id).count()

        # check the subscription limitations
        subscription = Subscription(req_user.orgs.chargebee_subscription_id)
        max_users = subscription.max_users()

        if max_users == -1:
            # infinite users
            pass
        elif existing_user_count >= max_users:
            logger.info(f"Organisation {req_user.orgs.name} has reached the user limit for their product tier.")
            raise ProductTierLimitError(f"You have reached the limit of users you can create.")

        with session_scope() as session:
            user = User(
                org_id=req_user.org_id,
                email=request_body["email"],
                first_name=request_body["first_name"],
                last_name=request_body["last_name"],
                role=request_body["role_id"],
                job_title=request_body.get("job_title"),
                disabled=request_body.get("disabled"),
                created_by=req_user.id,
            )
            session.add(user)

        with session_scope() as session:
            password_token = UserPasswordToken(user.id)
            session.add(password_token)

        # create user settings
        user.create_settings()

        # increment chargebee subscription plan_quantity
        subscription_api.increment_plan_quantity(user.orgs.chargebee_subscription_id)

        # send welcome email
        email_api.send_welcome_new_user(
            email=user.email,
            first_name=user.first_name,
            inviter_name=req_user.first_name,
            link=app.config["PUBLIC_WEB_URL"] + "/account-setup?token=" + password_token.token,
        )

        req_user.log(operation=Operations.CREATE, resource=Resources.USER, resource_id=user.id)

        Activity(
            org_id=user.org_id,
            event=Events.user_created,
            event_id=user.id,
            event_friendly=f"Created by {req_user.name()}.",
        ).publish()

        Activity(
            org_id=req_user.org_id,
            event=Events.user_created_user,
            event_id=req_user.id,
            event_friendly=f"Created {user.name()}.",
        ).publish()
        logger.info(f"User {req_user.id} created user {user.id}")

        return self.created(user.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @users_route.expect(update_user_request)
    @users_route.response(200, "User Updated", user_response)
    @users_route.response(400, "Bad request", message_response_dto)
    @users_route.response(403, "Insufficient privileges", message_response_dto)
    @users_route.response(404, "User does not exist", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Update a user. """
        req_user = kwargs["req_user"]

        user_attrs = self.validate_update_user_request(request.get_json(), **kwargs)

        # get the user to update
        user_to_update = user_service.get_by_id(user_attrs["id"])
        is_user_only_org_admin = user_service.is_user_only_org_admin(user_to_update)

        # if the user is going to be disabled
        if user_to_update.disabled is None and user_attrs["disabled"] is not None:
            if is_user_only_org_admin:
                raise ValidationError("Cannot disable only remaining Administrator.")

            # decrement plan quantity
            subscription_api.decrement_plan_quantity(user_to_update.orgs.chargebee_subscription_id)

            # drop the tasks
            with session_scope() as session:
                users_tasks = session.query(Task).filter_by(assignee=user_to_update.id).all()
            for task in users_tasks:
                task.drop(req_user)

        # user is being re-enabled
        elif user_to_update.disabled is not None and user_attrs["disabled"] is None:
            # increment plan quantity
            subscription_api.increment_plan_quantity(user_to_update.orgs.chargebee_subscription_id)

        # for all attributes in the request, update them on the user if they exist
        with session_scope():
            for k, v in user_attrs.items():
                user_to_update.__setattr__(k, v)
            user_to_update.updated_at = datetime.datetime.utcnow()
            user_to_update.updated_by = req_user.id

        Activity(
            org_id=user_to_update.org_id,
            event=Events.user_updated,
            event_id=user_to_update.id,
            event_friendly=f"Updated by {req_user.name()}",
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_updated_user,
            event_id=req_user.id,
            event_friendly=f"Updated {user_to_update.name()}.",
        ).publish()
        req_user.log(operation=Operations.UPDATE, resource=Resources.USER, resource_id=user_to_update.id)
        logger.info(f"User {req_user.id} updated user {user_to_update.id}")
        return self.ok(user_to_update.fat_dict())
