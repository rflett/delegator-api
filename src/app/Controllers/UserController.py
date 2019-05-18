import json
import typing
from app import logger, g_response, session_scope, j_response
from app.Controllers import AuthController
from app.Models import User, Notification
from app.Models.Enums import Events
from app.Models.RBAC import Operation, Resource, Permission
from flask import request, Response
from sqlalchemy import exists, func


def _compare_user_orgs(user_resource: User, request_user: User) -> bool:
    """
    Checks to see if the user making the request belongs to the same organisation as the user they're
    affecting. The exception to this rule is for the global superuser account.
    :param user_resource:   The user affected by the request_user
    :param request_user:    The user making the request
    :return:                True if the orgs are equal or false
    """
    return True if request_user.org_id == user_resource.org_id or request_user.role == 'ADMIN' else False


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
    def get_user(user_identifier: typing.Union[str, int]) -> User:
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

    @staticmethod
    def get_user_by_email(email: str) -> User:
        return _get_user_by_email(email)

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        return _get_user_by_id(user_id)

    @staticmethod
    def user_create(req: request, require_auth: bool = True) -> Response:
        """ Creates a user from a request """
        def create_user_settings(user_id) -> None:
            """ Creates user settings for this user """
            from app.Controllers import SettingsController
            from app.Models import UserSetting
            SettingsController.set_user_settings(UserSetting(user_id=user_id))

        def create_user(user_to_create: dict, request_user: User = None) -> Response:
            """ Creates the user """
            with session_scope() as session:
                user = User(
                    org_id=user_to_create.get('org_id'),
                    email=user_to_create.get('email'),
                    first_name=user_to_create.get('first_name'),
                    last_name=user_to_create.get('last_name'),
                    password=user_to_create.get('password'),
                    role=user_to_create.get('role'),
                    job_title=user_to_create.get('job_title')
                )
                session.add(user)

            # create user settings
            create_user_settings(user.id)

            if request_user is not None:
                request_user.log(
                    operation=Operation.CREATE,
                    resource=Resource.USER,
                    resource_id=user.id
                )
                Notification(
                    org_id=user.org_id,
                    event=Events.user_created,
                    payload=user.fat_dict(),
                    friendly=f"Created by {request_user.name()}."
                ).publish()
                Notification(
                    org_id=req_user.org_id,
                    event=Events.user_created_user,
                    payload=req_user.fat_dict(),
                    friendly=f"Created {user.name()}."
                ).publish()
                logger.info(f"user {request_user.id} created user {user.as_dict()}")
            else:
                user.log(
                    operation=Operation.CREATE,
                    resource=Resource.USER,
                    resource_id=user.id
                )
                # publish event
                Notification(
                    org_id=user.org_id,
                    event=Events.user_created,
                    payload=user.fat_dict(),
                    friendly=f"Created by {user.name()}"
                ).publish()
                logger.info(f"user {user.id} created user {user.as_dict()}")
            return g_response("Successfully created user", 201)

        request_body = req.get_json()

        # validate user
        from app.Controllers import ValidationController

        valid_user = ValidationController.validate_create_user_request(request_body)
        # invalid
        if isinstance(valid_user, Response):
            return valid_user

        if require_auth:
            logger.info("requiring auth to create user")
            req_user = AuthController.authorize_request(
                request_headers=req.headers,
                operation=Operation.CREATE,
                resource=Resource.USER,
                resource_org_id=valid_user.get('org_id')
            )
            # no perms
            if isinstance(req_user, Response):
                return req_user

            return create_user(
                user_to_create=valid_user,
                request_user=req_user
            )
        else:
            logger.info("not requiring auth to create user")
            return create_user(valid_user)

    @staticmethod
    def user_update(user_id: int, req: request) -> Response:
        """ Updates a user, requires the full user object in the response body.  """
        from app.Controllers import ValidationController

        request_body = req.get_json()

        try:
            user_id = int(user_id)
        except ValueError:
            return g_response(f"cannot cast `{user_id}` to int", 400)

        valid_user = ValidationController.validate_update_user_request(user_id, request_body)
        # invalid
        if isinstance(valid_user, Response):
            return valid_user

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.UPDATE,
            resource=Resource.USER,
            resource_org_id=valid_user.get('org_id'),
            resource_user_id=user_id
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        user_to_update = UserController.get_user_by_id(user_id)

        with session_scope():
            for k, v in valid_user.items():
                user_to_update.__setattr__(k, v)

        Notification(
            org_id=user_to_update.org_id,
            event=Events.user_updated,
            payload=user_to_update.fat_dict(),
            friendly=f"Updated by {req_user.name()}"
        ).publish()
        Notification(
            org_id=req_user.org_id,
            event=Events.user_updated_user,
            payload=req_user.fat_dict(),
            friendly=f"Updated {user_to_update.name()}."
        ).publish()
        req_user.log(
            operation=Operation.UPDATE,
            resource=Resource.USER,
            resource_id=user_id
        )
        logger.info(f"user {req_user.id} updated user {user_to_update.as_dict()}")
        return g_response(status=204)

    @staticmethod
    def user_delete(user_id: int, req: request) -> Response:
        """ Deletes a user """
        from app.Controllers import ValidationController

        try:
            user_id = int(user_id)
        except ValueError:
            return g_response(f"cannot cast `{user_id}` to int", 400)

        valid_user = ValidationController.validate_delete_user_request(user_id)
        # invalid
        if isinstance(valid_user, Response):
            return valid_user

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.DELETE,
            resource=Resource.USER,
            resource_org_id=valid_user.get('org_id')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope():
            user_to_del = UserController.get_user_by_id(user_id)
            Notification(
                org_id=req_user.org_id,
                event=Events.user_deleted_user,
                payload=req_user.fat_dict(),
                friendly=f"Deleted {user_to_del.first_name}."
            ).publish()
            user_to_del.anonymize()

        Notification(
            org_id=user_to_del.org_id,
            event=Events.user_deleted,
            payload=user_to_del.fat_dict(),
            friendly=f"Deleted by {req_user.name()}."
        ).publish()
        req_user.log(
            operation=Operation.DELETE,
            resource=Resource.USER,
            resource_id=user_id
        )
        logger.info(f"user {req_user.id} deleted user {user_to_del.as_dict()}")
        return g_response(status=204)

    @staticmethod
    def user_get(user_identifier: typing.Union[int, str], req: request) -> Response:
        """ Get a single user by email or ID """
        from app.Controllers import UserController

        # is the identifier an email or user_id?
        try:
            user_identifier = int(user_identifier)
            logger.info("user_identifier is an id")
        except ValueError:
            from app.Controllers import ValidationController
            validate_identifier = ValidationController.validate_email(user_identifier)
            if isinstance(validate_identifier, Response):
                return validate_identifier
            else:
                logger.info("user_identifier is an email")
                user_identifier = str(user_identifier)

        if UserController.user_exists(user_identifier):
            user = UserController.get_user(user_identifier)
            req_user = AuthController.authorize_request(
                request_headers=req.headers,
                operation=Operation.GET,
                resource=Resource.USER,
                resource_user_id=user.id,
                resource_org_id=user.org_id
            )
            # no perms
            if isinstance(req_user, Response):
                return req_user

            req_user.log(
                operation=Operation.GET,
                resource=Resource.USER,
                resource_id=user.id
            )
            logger.info(f"found user {user.as_dict()}")
            return j_response(user.as_dict())
        else:
            logger.info(f"user with id {user_identifier} does not exist")
            return g_response("User does not exist.", 400)

    @staticmethod
    def user_get_all(req: request) -> Response:
        """
        Get all users
        :param req:     The request object
        :return:
        """
        from app.Controllers import AuthController
        from app.Models import User

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.USERS
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope() as session:
            users_qry = session.query(User) \
                .filter(User.org_id == req_user.org_id) \
                .all()

        users = [u.fat_dict() for u in users_qry]
        req_user.log(
            operation=Operation.GET,
            resource=Resource.USERS
        )
        logger.info(f"found {len(users)} users: {json.dumps(users)}")
        return j_response(users)

    @staticmethod
    def user_pages(req: request) -> Response:
        """ Returns the pages a user can access """
        from app.Controllers import AuthController

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.PAGES
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

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
                operation=Operation.GET,
                resource=Resource.PAGES
            )
            logger.info(f"found {len(pages)} pages: {pages}")
            return j_response(sorted(pages))

    @staticmethod
    def get_user_settings(req: request) -> Response:
        """ Returns the user's settings """
        from app.Controllers import AuthController, SettingsController

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.USER_SETTINGS
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        req_user.log(
            operation=Operation.GET,
            resource=Resource.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"got user settings for {req_user.id}")
        return j_response(SettingsController.get_user_settings(req_user.id).as_dict())

    @staticmethod
    def update_user_settings(req: request) -> Response:
        """ Returns the user's settings """
        from app.Controllers import AuthController, ValidationController, SettingsController

        valid_user_settings = ValidationController.validate_update_user_settings_request(req.get_json())
        # invalid
        if isinstance(valid_user_settings, Response):
            return valid_user_settings

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.UPDATE,
            resource=Resource.USER_SETTINGS,
            resource_org_id=valid_user_settings.get('org_id'),
            resource_user_id=valid_user_settings.get('user_id')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        SettingsController.set_user_settings(valid_user_settings.get('user_settings'))
        req_user.log(
            operation=Operation.UPDATE,
            resource=Resource.USER_SETTINGS,
            resource_id=req_user.id
        )
        logger.info(f"updated user {req_user.id} settings")
        return g_response(status=204)

    @staticmethod
    def get_user_activity(user_identifier: typing.Union[str, int], req: request) -> Response:
        """ Returns the activity for a user """
        from app.Controllers import UserController

        # is the identifier an email or user_id?
        try:
            user_identifier = int(user_identifier)
            logger.info("user_identifier is an id")
        except ValueError:
            from app.Controllers import ValidationController
            validate_identifier = ValidationController.validate_email(user_identifier)
            if isinstance(validate_identifier, Response):
                return validate_identifier
            else:
                logger.info("user_identifier is an email")
                user_identifier = str(user_identifier)

        if UserController.user_exists(user_identifier):
            user = UserController.get_user(user_identifier)
            req_user = AuthController.authorize_request(
                request_headers=req.headers,
                operation=Operation.GET,
                resource=Resource.USER_ACTIVITY,
                resource_user_id=user.id,
                resource_org_id=user.org_id
            )
            # no perms
            if isinstance(req_user, Response):
                return req_user

            req_user.log(
                operation=Operation.GET,
                resource=Resource.USER_ACTIVITY,
                resource_id=user.id
            )
            logger.info(f"getting activity for user with id {user.id}")
            return j_response(user.activity())
        else:
            logger.info(f"user with id {user_identifier} does not exist")
            return g_response("User does not exist.", 400)
