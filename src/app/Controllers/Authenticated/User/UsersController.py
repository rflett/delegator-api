import datetime

from flask import Response, request
from flask_restplus import Namespace

from app import session_scope, subscription_api, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Exceptions import ProductTierLimitError
from app.Models import User, Activity, Task
from app.Models.Enums import Operations, Resources, Events
from app.Models.Request import create_user_request, update_user_request
from app.Models.Response import message_response_dto, user_response, get_users_response
from app.Services.UserService import UserService

users_route = Namespace(
    path="/users",
    name="Users",
    description="Used to manage users"
)

user_service = UserService()


@users_route.route("/")
class UserController(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.USERS)
    @users_route.response(200, "Users retrieved", get_users_response)
    @users_route.response(400, "Couldn't retrieve the users", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Get all users """
        req_user = kwargs['req_user']

        # query for all users in the requesting user's organisation
        with session_scope() as session:
            users_qry = session.query(User) \
                .filter_by(
                org_id=req_user.org_id,
                deleted=None
            ).all()

        users = []

        for user in users_qry:
            with session_scope() as session:
                created_by = session.query(User).filter_by(id=user.created_by).first()
                updated_by = session.query(User).filter_by(id=user.updated_by).first()

            user_dict = user.as_dict()
            # TODO change to user not their name?
            user_dict['created_by'] = created_by.name()
            user_dict['updated_by'] = updated_by.name() if updated_by is not None else None
            user_dict['role'] = user.roles.as_dict()
            users.append(user_dict)

        logger.info(f"found {len(users)} users.")
        req_user.log(
            operation=Operations.GET,
            resource=Resources.USERS
        )
        return self.ok({
            "users": users
        })

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.CREATE, Resources.USER)
    @users_route.expect(create_user_request)
    @users_route.response(200, "User created", user_response)
    @users_route.response(402, "Plan limit reached. Need to pay more", message_response_dto)
    @users_route.response(400, "Couldn't create the user", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Create a user"""
        request_body = request.get_json()

        req_user = kwargs['req_user']

        # validate user
        self.validate_create_user_request(req_user, request_body)

        # Check that the user hasn't surpassed limits on their product tier
        with session_scope() as session:
            existing_user_count = session.query(User).filter_by(org_id=req_user.org_id).count()

        max_users = subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('max_users', 10)

        if existing_user_count >= max_users:
            logger.info(f"Organisation {req_user.orgs.name} has reached the user limit for their product tier.")
            raise ProductTierLimitError(f"You have reached the limit of users you can create.")

        with session_scope() as session:
            user = User(
                org_id=req_user.org_id,
                email=request_body['email'],
                first_name=request_body['first_name'],
                last_name=request_body['last_name'],
                password=request_body['password'],
                role=request_body['role_id'],
                job_title=request_body['job_title'],
                disabled=request_body.get('disabled'),
                created_by=req_user.id
            )
            session.add(user)

        # create user settings
        user.create_settings()

        # increment chargebee subscription plan_quantity
        subscription_api.increment_plan_quantity(user.orgs.chargebee_subscription_id)

        req_user.log(
            operation=Operations.CREATE,
            resource=Resources.USER,
            resource_id=user.id
        )

        Activity(
            org_id=user.org_id,
            event=Events.user_created,
            event_id=user.id,
            event_friendly=f"Created by {req_user.name()}."
        ).publish()

        Activity(
            org_id=req_user.org_id,
            event=Events.user_created_user,
            event_id=req_user.id,
            event_friendly=f"Created {user.name()}."
        ).publish()
        logger.info(f"User {req_user.id} created user {user.id}")

        return self.created(user.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @users_route.expect(update_user_request)
    @users_route.response(200, "User Updated", user_response)
    @users_route.response(400, "Couldn't update the user", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Update a user. """
        req_user = kwargs['req_user']

        user_attrs = self.validate_update_user_request(request.get_json(), **kwargs)

        # get the user to update
        user_to_update = user_service.get_by_id(user_attrs['id'])

        # if the user is going to be disabled
        if user_to_update.disabled is None and user_attrs['disabled'] is not None:
            # decrement plan quantity
            subscription_api.decrement_plan_quantity(user_to_update.orgs.chargebee_subscription_id)

            # drop the tasks
            with session_scope() as session:
                users_tasks = session.query(Task).filter_by(assignee=user_to_update.id).all()
            for task in users_tasks:
                task.drop(req_user)

        # user is being re-enabled
        elif user_to_update.disabled is not None and user_attrs['disabled'] is None:
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
            event_friendly=f"Updated by {req_user.name()}"
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_updated_user,
            event_id=req_user.id,
            event_friendly=f"Updated {user_to_update.name()}."
        ).publish()
        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.USER,
            resource_id=user_to_update.id
        )
        logger.info(f"User {req_user.id} updated user {user_to_update.id}")
        return self.ok(user_to_update.fat_dict())
