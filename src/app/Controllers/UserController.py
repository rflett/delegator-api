import datetime

from flask import request, Response

from app import logger, g_response, session_scope, j_response, subscription_api
from app.Controllers import AuthorizationController
from app.Exceptions import ProductTierLimitError, ResourceNotFoundError
from app.Models import User, Activity, Task
from app.Models.Enums import Events, Operations, Resources
from app.Models.RBAC import Permission


def _get_user_by_id(user_id: int) -> User:
    """Gets a user by their id

    :param user_id:         The user's id
    :return:                The User
    """
    with session_scope() as session:
        ret = session.query(User).filter_by(id=user_id, deleted=None).first()

    if ret is None:
        raise ResourceNotFoundError(f"User with id {user_id} does not exist.")
    else:
        return ret


class UserController(object):
    @staticmethod
    def get_user_by_email(email: str) -> User:
        """Public method for getting a user by their email """
        with session_scope() as session:
            ret = session.query(User).filter_by(email=email, deleted=None).first()
        if ret is None:
            raise ResourceNotFoundError(f"User with email {email} does not exist.")
        else:
            return ret

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """Public method for getting a user by their id """
        return _get_user_by_id(user_id)

    @staticmethod
    def create_user(req: request) -> Response:
        """Create a user """
        from app.Controllers import AuthenticationController, ValidationController

        request_body = req.get_json()

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.CREATE,
            resource=Resources.USER
        )

        # validate user
        ValidationController.validate_create_user_request(request_body)

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

        return j_response(user.fat_dict(), status=201)

    @staticmethod
    def create_signup_user(org_id: int, valid_user: dict) -> None:
        """Creates a user from the signup page """
        with session_scope() as session:
            user = User(
                org_id=org_id,
                email=valid_user.get('email'),
                first_name=valid_user.get('first_name'),
                last_name=valid_user.get('last_name'),
                password=valid_user.get('password'),
                role=valid_user.get('role'),
                job_title=valid_user.get('job_title')
            )
            session.add(user)

        with session_scope():
            user.created_by = user.id

        # create user settings
        user.create_settings()

        user.log(
            operation=Operations.CREATE,
            resource=Resources.USER,
            resource_id=user.id
        )
        # publish event
        Activity(
            org_id=user.org_id,
            event=Events.user_created,
            event_id=user.id,
            event_friendly=f"Created by {user.name()}"
        ).publish()
        logger.info(f"User {user.id} signed up.")

    @staticmethod
    def update_user(req: request) -> Response:
        """Update a user. """
        from app.Controllers import ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        user_attrs = ValidationController.validate_update_user_request(req.get_json())

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.UPDATE,
            resource=Resources.USER,
            affected_user_id=user_attrs.get('id')
        )

        # get the user to update
        user_to_update = _get_user_by_id(user_attrs.get('id'))

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
        return j_response(user_to_update.fat_dict())

    @staticmethod
    def delete_user(user_id: int, req: request) -> Response:
        """Deletes a user """
        from app.Controllers import AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.DELETE,
            resource=Resources.USER,
            affected_user_id=user_id
        )

        # get the user
        user_to_delete = _get_user_by_id(user_id)

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
        return g_response(status=204)

    @staticmethod
    def get_user(user_id: int, req: request) -> Response:
        """Get a single user by email or ID """
        from app.Controllers import AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.USER,
            affected_user_id=user_id
        )

        user = _get_user_by_id(user_id)
        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER,
            resource_id=user.id
        )
        logger.info(f"Found user {user.id}")
        return j_response(user.fat_dict())

    @staticmethod
    def get_users(req: request) -> Response:
        """Get all users """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import User

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.USERS
        )

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
        return j_response(users)

    @staticmethod
    def user_pages(req: request) -> Response:
        """Returns the pages a user can access """
        from app.Controllers import AuthorizationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.PAGES
        )

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
            return j_response(sorted(pages))

    @staticmethod
    def get_user_settings(req: request) -> Response:
        """Returns the user's settings """
        from app.Controllers import AuthorizationController, SettingsController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.USER_SETTINGS,
            affected_user_id=req_user.id
        )

        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"got user settings for {req_user.id}")
        return j_response(SettingsController.get_user_settings(req_user.id).as_dict())

    @staticmethod
    def update_user_settings(req: request) -> Response:
        """Updates the user's settings """
        from app.Controllers import AuthorizationController, ValidationController, SettingsController, \
            AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.UPDATE,
            resource=Resources.USER_SETTINGS,
            affected_user_id=req_user.id
        )

        user_setting = ValidationController.validate_update_user_settings_request(req_user.id, req.get_json())

        SettingsController.set_user_settings(user_setting)
        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"updated user {req_user.id} settings")
        return j_response(SettingsController.get_user_settings(req_user.id).as_dict())

    @staticmethod
    def get_user_activity(user_id: int, req: request) -> Response:
        """Returns the activity for a user """
        from app.Controllers import AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        if not subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('view_user_activity', False):
            raise ProductTierLimitError(f"You cannot view user activity on your plan.")

        user = _get_user_by_id(user_id)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.USER_ACTIVITY,
            affected_user_id=user.id
        )

        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER_ACTIVITY,
            resource_id=user.id
        )
        logger.info(f"getting activity for user with id {user.id}")
        return j_response(user.activity())
