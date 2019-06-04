import json
import typing

from flask import request, Response
from sqlalchemy import exists, func

from app import logger, g_response, session_scope, j_response
from app.Controllers import AuthorizationController
from app.Exceptions import AuthenticationError, AuthorizationError
from app.Models import User, Notification
from app.Models.Enums import Events, Operations, Resources
from app.Models.RBAC import Permission


def _get_user_by_email(email: str) -> User:
    """
    Gets a user by their email address
    :param email:          The user's email
    :raises ValueError:     If the user doesn't exist.
    :return:                The User
    """
    with session_scope() as session:
        ret = session.query(User).filter(User.email == email).first()
    if ret is None:
        logger.info(f"User with email {email} does not exist.")
        raise ValueError(f"User with email {email} does not exist.")
    else:
        return ret


def _get_user_by_id(user_id: int) -> User:
    """
    Gets a user by their id
    :param user_id:         The user's id
    :raises ValueError:     If the user doesn't exist.
    :return:                The User
    """
    with session_scope() as session:
        ret = session.query(User).filter(User.id == user_id).first()
    if ret is None:
        logger.info(f"User with id {user_id} does not exist.")
        raise ValueError(f"User with id {user_id} does not exist.")
    else:
        return ret


def _get_user(user_identifier: typing.Union[str, int]) -> User:
    """
    Gets a user by their id or email
    :param user_identifier: The user id or email
    :raises ValueError:     If the user doesn't exist.
    """
    if isinstance(user_identifier, str):
        logger.info("user_identifier is a str so getting user by email")
        return _get_user_by_email(user_identifier)
    elif isinstance(user_identifier, int):
        logger.info("user_identifier is an int so getting user by id")
        return _get_user_by_id(user_identifier)
    else:
        raise ValueError(f"bad user_identifier, expected Union[str, int] got {type(user_identifier)}")


class UserController(object):
    @staticmethod
    def user_exists(user_identifier: typing.Union[str, int]) -> bool:
        """
        Checks to see if a user exists
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
        return _get_user_by_email(email)

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        return _get_user_by_id(user_id)

    @staticmethod
    def create_user(req: request) -> Response:
        """ Creates a user from a request """
        from app.Controllers import AuthenticationController, ValidationController
        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.CREATE,
                resource=Resources.USER
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        # validate user
        user_attrs = ValidationController.validate_create_user_request(req.get_json())
        # invalid
        if isinstance(user_attrs, Response):
            return user_attrs

        with session_scope() as session:
            user = User(
                org_id=req_user.org_id,
                email=user_attrs.get('email'),
                first_name=user_attrs.get('first_name'),
                last_name=user_attrs.get('last_name'),
                password='secret',
                role=user_attrs.get('role'),
                job_title=user_attrs.get('job_title')
            )
            session.add(user)

        # create user settings
        user.create_settings()

        req_user.log(
            operation=Operations.CREATE,
            resource=Resources.USER,
            resource_id=user.id
        )
        Notification(
            org_id=user.org_id,
            event=Events.user_created,
            event_id=user.id,
            event_friendly=f"Created by {req_user.name()}."
        ).publish()
        Notification(
            org_id=req_user.org_id,
            event=Events.user_created_user,
            event_id=req_user.id,
            event_friendly=f"Created {user.name()}."
        ).publish()
        logger.info(f"user {req_user.id} created user {user.as_dict()}")

        return g_response("Successfully created user", 201)

    @staticmethod
    def create_signup_user(org_id: int, valid_user: dict) -> None:
        """ Creates a user from the signup page """
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

        # create user settings
        user.create_settings()

        user.log(
            operation=Operations.CREATE,
            resource=Resources.ORGANISATION,
            resource_id=org_id
        )
        user.log(
            operation=Operations.CREATE,
            resource=Resources.USER,
            resource_id=user.id
        )
        # publish event
        Notification(
            org_id=user.org_id,
            event=Events.user_created,
            event_id=user.id,
            event_friendly=f"Created by {user.name()}"
        ).publish()
        logger.info(f"user {user.id} created user {user.as_dict()}")

    @staticmethod
    def update_user(req: request) -> Response:
        """ Updates a user, requires the full user object in the response body.  """
        from app.Controllers import ValidationController, AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        user_attrs = ValidationController.validate_update_user_request(req.get_json())
        # invalid
        if isinstance(user_attrs, Response):
            return user_attrs

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.UPDATE,
                resource=Resources.USER,
                affected_user_id=user_attrs.get('id')
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        user_to_update = UserController.get_user_by_id(user_attrs.get('id'))

        with session_scope():
            for k, v in user_attrs.items():
                user_to_update.__setattr__(k, v)

        Notification(
            org_id=user_to_update.org_id,
            event=Events.user_updated,
            event_id=user_to_update.id,
            event_friendly=f"Updated by {req_user.name()}"
        ).publish()
        Notification(
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
        logger.info(f"user {req_user.id} updated user {user_to_update.as_dict()}")
        return g_response(status=204)

    @staticmethod
    def delete_user(user_id: int, req: request) -> Response:
        """ Deletes a user """
        from app.Controllers import AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.DELETE,
                resource=Resources.USER,
                affected_user_id=user_id
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        user_to_delete = UserController.get_user_by_id(user_id)

        with session_scope():
            Notification(
                org_id=req_user.org_id,
                event=Events.user_deleted_user,
                event_id=req_user.id,
                event_friendly=f"Deleted user id {user_to_delete.id}."
            ).publish()
            user_to_delete.anonymize()

        req_user.log(
            operation=Operations.DELETE,
            resource=Resources.USER,
            resource_id=user_to_delete.id
        )
        logger.info(f"user {req_user.id} deleted user id {user_to_delete.id}")
        return g_response(status=204)

    @staticmethod
    def get_user(user_identifier: typing.Union[int, str], req: request) -> Response:
        """ Get a single user by email or ID """
        from app.Controllers import AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        # is the identifier an email or user_id?
        try:
            user_identifier = int(user_identifier)
        except ValueError:
            from app.Controllers import ValidationController
            validate_identifier = ValidationController.validate_email(user_identifier)
            if isinstance(validate_identifier, Response):
                return validate_identifier
            else:
                user_identifier = str(user_identifier)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.GET,
                resource=Resources.USER,
                affected_user_id=user_identifier
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        try:
            user = _get_user(user_identifier)
            req_user.log(
                operation=Operations.GET,
                resource=Resources.USER,
                resource_id=user.id
            )
            logger.info(f"found user {user.as_dict()}")
            return j_response(user.as_dict())
        except ValueError as e:
            return g_response(str(e), 400)

    @staticmethod
    def get_all_users(req: request) -> Response:
        """
        Get all users
        :param req:     The request object
        :return:
        """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import User

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.GET,
                resource=Resources.USERS
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        with session_scope() as session:
            users_qry = session.query(User) \
                .filter(User.org_id == req_user.org_id) \
                .all()

        users = [u.fat_dict() for u in users_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.USERS
        )
        logger.info(f"found {len(users)} users: {json.dumps(users)}")
        return j_response(users)

    @staticmethod
    def user_pages(req: request) -> Response:
        """ Returns the pages a user can access """
        from app.Controllers import AuthorizationController, AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.GET,
                resource=Resources.PAGES
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

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

            req_user.log(
                operation=Operations.GET,
                resource=Resources.PAGES
            )
            logger.info(f"found {len(pages)} pages: {pages}")
            return j_response(sorted(pages))

    @staticmethod
    def get_user_settings(req: request) -> Response:
        """ Returns the user's settings """
        from app.Controllers import AuthorizationController, SettingsController, AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.GET,
                resource=Resources.USER_SETTINGS,
                affected_user_id=req_user.id
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"got user settings for {req_user.id}")
        return j_response(SettingsController.get_user_settings(req_user.id).as_dict())

    @staticmethod
    def update_user_settings(req: request) -> Response:
        """ Returns the user's settings """
        from app.Controllers import AuthorizationController, ValidationController, SettingsController, \
            AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.UPDATE,
                resource=Resources.USER_SETTINGS,
                affected_user_id=req_user.id
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        user_setting = ValidationController.validate_update_user_settings_request(req_user.id, req.get_json())

        SettingsController.set_user_settings(user_setting)
        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"updated user {req_user.id} settings")
        return g_response(status=204)

    @staticmethod
    def get_user_activity(user_identifier: typing.Union[str, int], req: request) -> Response:
        """ Returns the activity for a user """
        from app.Controllers import AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        # is the identifier an email or user_id?
        try:
            user_identifier = int(user_identifier)
        except ValueError:
            from app.Controllers import ValidationController
            validate_identifier = ValidationController.validate_email(user_identifier)
            if isinstance(validate_identifier, Response):
                return validate_identifier
            else:
                user_identifier = str(user_identifier)

        try:
            user = _get_user(user_identifier)
        except ValueError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.GET,
                resource=Resources.USER_ACTIVITY,
                affected_user_id=user.id
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER_ACTIVITY,
            resource_id=user.id
        )
        logger.info(f"getting activity for user with id {user.id}")
        return j_response(user.activity())
