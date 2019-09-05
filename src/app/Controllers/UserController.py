import datetime
import typing

from flask import request, Response
from sqlalchemy import exists, func

from app import logger, g_response, session_scope, j_response, subscription_api
from app.Controllers import AuthorizationController
from app.Exceptions import ProductTierLimitError
from app.Models import User, Activity, Task
from app.Models.Enums import Events, Operations, Resources
from app.Models.RBAC import Permission


def _get_user_by_email(email: str) -> User:
    """Gets a user by their email address

    :param email:           The user's email
    :raises ValueError:     If the user doesn't exist.
    :return:                The User
    """
    with session_scope() as session:
        ret = session.query(User).filter_by(
            email=email,
            deleted=None
        ).first()
    if ret is None:
        logger.info(f"User with email {email} does not exist.")
        raise ValueError(f"User with email {email} does not exist.")
    else:
        return ret


def _get_user_by_id(user_id: int) -> User:
    """Gets a user by their id

    :param user_id:         The user's id
    :raises ValueError:     If the user doesn't exist.
    :return:                The User
    """
    with session_scope() as session:
        ret = session.query(User).filter_by(
            id=user_id,
            deleted=None
        ).first()
    if ret is None:
        logger.info(f"User with id {user_id} does not exist.")
        raise ValueError(f"User with id {user_id} does not exist.")
    else:
        return ret


def _get_user(user_identifier: typing.Union[str, int]) -> User:
    """Gets a user by their id or email

    :param user_identifier: The user id or email
    :raises ValueError:     If the user doesn't exist.
    """
    if isinstance(user_identifier, str):
        return _get_user_by_email(user_identifier)
    elif isinstance(user_identifier, int):
        return _get_user_by_id(user_identifier)
    else:
        raise ValueError(f"Bad user_identifier, expected Union[str, int] got {type(user_identifier)}")


class UserController(object):
    @staticmethod
    def user_exists(user_identifier: typing.Union[str, int]) -> bool:
        """Checks to see if a user exists

        :param user_identifier: The user id or email
        :raises ValueError:     If the user doesn't exist.
        """
        with session_scope() as session:
            if isinstance(user_identifier, str):
                logger.info("user_identifier is a str so finding user by email")
                return session.query(exists().where(func.lower(User.email) == func.lower(user_identifier))).scalar()
            elif isinstance(user_identifier, int):
                logger.info("user_identifier is an int so finding user by id")
                return session.query(exists().where(User.id == user_identifier)).scalar()
            else:
                raise ValueError(f"bad user_identifier, expected Union[str, int] got {type(user_identifier)}")

    @staticmethod
    def get_user_by_email(email: str) -> User:
        """Public method for getting a user by their email """
        return _get_user_by_email(email)

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """Public method for getting a user by their id """
        return _get_user_by_id(user_id)

    @staticmethod
    def all_user_ids(org_id: int) -> typing.List[int]:
        """ Returns a list of all user ids """
        with session_scope() as session:
            user_ids_qry = session.query(User.id).filter_by(org_id=org_id).all()

        return [user_id[0] for user_id in user_ids_qry]

    @staticmethod
    def create_user(req: request) -> Response:
        """Create a user """
        from app.Controllers import AuthenticationController, ValidationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.CREATE,
            resource=Resources.USER
        )

        # Check that the user hasn't surpassed limits on their product tier
        with session_scope() as session:
            existing_user_count = session.query(User).filter_by(org_id=req_user.org_id).count()

        max_users = subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('max_users', 10)

        if existing_user_count >= max_users:
            logger.info(f"Organisation {req_user.orgs.name} has reached the user limit for their product tier.")
            raise ProductTierLimitError(f"You have reached the limit of users you can create.")

        # validate user
        user_attrs = ValidationController.validate_create_user_request(req.get_json())

        with session_scope() as session:
            user = User(
                org_id=req_user.org_id,
                email=user_attrs.get('email'),
                first_name=user_attrs.get('first_name'),
                last_name=user_attrs.get('last_name'),
                password='secret',
                role=user_attrs.get('role'),
                job_title=user_attrs.get('job_title'),
                disabled=user_attrs.get('disabled'),
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
        user_to_update = UserController.get_user_by_id(user_attrs.get('id'))

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
        user_to_delete = UserController.get_user_by_id(user_id)

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
    def get_user(user_identifier: typing.Union[int, str], req: request) -> Response:
        """Get a single user by email or ID """
        from app.Controllers import AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        # is the identifier an email or user_id?
        try:
            user_identifier = int(user_identifier)
        except ValueError:
            from app.Controllers import ValidationController
            if ValidationController.validate_email(user_identifier):
                user_identifier = str(user_identifier)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.USER,
            affected_user_id=user_identifier
        )

        try:
            user = _get_user(user_identifier)
            req_user.log(
                operation=Operations.GET,
                resource=Resources.USER,
                resource_id=user.id
            )
            logger.info(f"Found user {user.id}")
            return j_response(user.fat_dict())
        except ValueError as e:
            return g_response(str(e), 400)

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
    def get_user_activity(user_identifier: typing.Union[str, int], req: request) -> Response:
        """Returns the activity for a user """
        from app.Controllers import AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        if not subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('view_user_activity', False):
            raise ProductTierLimitError(f"You cannot view user activity on your plan.")

        # is the identifier an email or user_id?
        try:
            user_identifier = int(user_identifier)
        except ValueError:
            from app.Controllers import ValidationController
            if ValidationController.validate_email(user_identifier):
                user_identifier = str(user_identifier)

        try:
            user = _get_user(user_identifier)
        except ValueError as e:
            return g_response(str(e), 400)

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
