import datetime
from decimal import Decimal

from flask import request, Response

from app import logger, session_scope, subscription_api
from app.Controllers.Base import RequestValidationController
from app.Exceptions import ProductTierLimitError
from app.Models import User, Activity, Task, UserSetting
from app.Models.Enums import Events, Operations, Resources
from app.Models.RBAC import Permission
from app.Services import UserService, SettingsService


class UserController(RequestValidationController):
    settings_service: SettingsService = None
    user_service: UserService = None

    def __init__(self):
        RequestValidationController.__init__(self)
        self.settings_service = SettingsService()
        self.user_service = UserService()

    def create_user(self, **kwargs) -> Response:
        """Create a user """
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
                password='secret',
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

    def update_user(self, **kwargs) -> Response:
        """Update a user. """
        req_user = kwargs['req_user']

        user_attrs = self.validate_update_user_request(request.get_json(), **kwargs)

        # get the user to update
        user_to_update = self.user_service.get_by_id(user_attrs['id'])

        # if the task is going to be disabled
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

    def delete_user(self, user_id: int, **kwargs) -> Response:
        """Deletes a user """
        req_user = kwargs['req_user']

        user_to_delete = self.validate_delete_user(user_id, **kwargs)

        user_to_delete.delete(req_user)

        with session_scope():
            Activity(
                org_id=req_user.org_id,
                event=Events.user_deleted_user,
                event_id=req_user.id,
                event_friendly=f"Deleted user {user_to_delete.name()}."
            ).publish()

        req_user.log(
            operation=Operations.DELETE,
            resource=Resources.USER,
            resource_id=user_to_delete.id
        )
        logger.info(f"User {req_user.id} deleted user {user_to_delete.id}.")
        return self.no_content()

    def get_user(self, user_id: int, **kwargs) -> Response:
        """Get a single user by email or ID """
        user = self.validate_get_user(user_id, **kwargs)
        kwargs['req_user'].log(
            operation=Operations.GET,
            resource=Resources.USER,
            resource_id=user.id
        )
        return self.ok(user.fat_dict())

    def get_users(self, **kwargs) -> Response:
        """Get all users """
        req_user = kwargs['req_user']

        # query for all users in the requesting user's organisation
        with session_scope() as session:
            users_qry = session.query(User)\
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
        return self.ok(users)

    def user_pages(self, **kwargs) -> Response:
        """Returns the pages a user can access """
        req_user = kwargs['req_user']

        # query for permissions that have the resource id like %_PAGE
        with session_scope() as session:
            pages_qry = session.query(Permission.resource_id).filter(
                Permission.role_id == req_user.role,
                Permission.resource_id.like("%_PAGE")
            ).all()

            pages = []
            for permission in pages_qry:
                for page in permission:
                    # strip _PAGE
                    pages.append(page.split('_PAGE')[0])

            if not subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('view_reports_page', False):
                pages.remove('REPORTS')

            req_user.log(
                operation=Operations.GET,
                resource=Resources.PAGES
            )
            logger.info(f"found {len(pages)} pages.")
            return self.ok(sorted(pages))

    def get_user_settings(self, **kwargs) -> Response:
        """Returns the user's settings """
        req_user = kwargs['req_user']
        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"got user settings for {req_user.id}")
        return self.ok(self.settings_service.get_user_settings(req_user.id).as_dict())

    def update_user_settings(self, **kwargs) -> Response:
        """Updates the user's settings """
        req_user = kwargs['req_user']

        new_settings = UserSetting(user_id=Decimal(req_user.id))
        for k, v in request.get_json().items():
            new_settings.__setattr__(k, v)

        self.settings_service.set_user_settings(new_settings)
        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"updated user {req_user.id} settings")
        return self.ok(new_settings.as_dict())

    def get_user_activity(self, user_id: int, **kwargs) -> Response:
        """Returns the activity for a user """
        req_user = kwargs['req_user']

        if not subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('view_user_activity', False):
            raise ProductTierLimitError(f"You cannot view user activity on your plan.")

        user = self.validate_get_user_activity(user_id, **kwargs)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER_ACTIVITY,
            resource_id=user.id
        )
        logger.info(f"getting activity for user with id {user.id}")
        return self.ok(user.activity())
