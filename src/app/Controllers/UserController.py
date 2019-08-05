import datetime
import typing

from flask import request, Response
from sqlalchemy import exists, func, and_
from sqlalchemy.orm import aliased

from app import logger, g_response, session_scope, j_response
from app.Controllers import AuthorizationController
from app.Models import User, Notification
from app.Models.Enums import Events, Operations, Resources
from app.Models.RBAC import Permission


def _get_user_by_email(email: str) -> User:
    """Gets a user by their email address

    :param email:           The user's email
    :raises ValueError:     If the user doesn't exist.
    :return:                The User
    """
    with session_scope() as session:
        ret = session.query(User).filter(and_(User.email == email, User.deleted == None)).first()  # noqa
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
        ret = session.query(User).filter(and_(User.id == user_id, User.deleted == None)).first()  # noqa
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
    def create_user(req: request) -> Response:
        """Create a user """
        from app.Controllers import AuthenticationController, ValidationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.CREATE,
            resource=Resources.USER
        )

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

        req_user.log(
            operation=Operations.CREATE,
            resource=Resources.USER,
            resource_id=user.id
        )

        # notifications
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
        logger.info(f"User {req_user.id} created user {user.id}")

        return g_response("Successfully created user", 201)

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

        # notifications
        Notification(
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

        # for all attributes in the request, update them on the user if they exist
        with session_scope():
            for k, v in user_attrs.items():
                user_to_update.__setattr__(k, v)
            user_to_update.updated_at = datetime.datetime.utcnow()
            user_to_update.updated_by = req_user.id

        # notifications
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
        logger.info(f"User {req_user.id} updated user {user_to_update.id}")
        return g_response(status=204)

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

        with session_scope():
            # delete the user
            user_to_delete.anonymize()
            Notification(
                org_id=req_user.org_id,
                event=Events.user_deleted_user,
                event_id=req_user.id,
                event_friendly=f"Deleted user id {user_to_delete.id}."
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
        from app.Models import User, Organisation
        from app.Models.RBAC import Role

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.USERS
        )

        # query for all users in the requesting user's organisation
        with session_scope() as session:
            created_by, updated_by = aliased(User), aliased(User)
            users_qry = session.query(User, Role, Organisation, created_by, updated_by) \
                .join(User.roles) \
                .join(User.orgs) \
                .join(User.created_by, created_by.id == User.created_by)\
                .outerjoin(User.updated_by, updated_by.id == User.updated_by)\
                .filter(
                    and_(
                        User.org_id == req_user.org_id,
                        User.deleted == None  # noqa
                    )
                ) \
                .all()

        # return object
        users = []

        # get objects for each sub object of the user
        for user, role, org in users_qry:
            user_dict = user.as_dict()
            user_dict['created_by'] = created_by.name()
            user_dict['updated_by'] = updated_by.name() if updated_by is not None else None
            user_dict['role'] = role.as_dict()
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
        return g_response(status=204)

    @staticmethod
    def get_user_activity(user_identifier: typing.Union[str, int], req: request) -> Response:
        """Returns the activity for a user """
        from app.Controllers import AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

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
