import json
import typing
from app import logger, g_response, session_scope, j_response
from app.Controllers import AuthController
from app.Models import User, Organisation
from app.Models.RBAC import Operation, Resource, Role, Permission
from flask import request, Response
from sqlalchemy import exists


def _compare_user_orgs(user_resource: User, request_user: User) -> bool:
    """
    Checks to see if the user making the request belongs to the same organisation as the user they're
    affecting. The exception to this rule is for the global superuser account.
    :param user_resource:   The user affected by the request_user
    :param request_user:    The user making the request
    :return:                True if the orgs are equal or false
    """
    return True if request_user.org_id == user_resource.org_id or request_user.role == 'ADMIN' else False


def _make_user_dict(user: User, role: Role, org: Organisation) -> dict:
    """
    Creates a dict of a user and the appropriate attributes. Probably not the best way to do this yet,
    needs refactoring once I understand its use more.
    :param user:    The user
    :param role:    The user's role
    :return:        A dict with the params merged
    """
    extras = {}

    # prepend role attrs with role_
    for k, v in role.as_dict().items():
        # key exclusions
        if k not in ['id', 'rank']:
            extras[f'role_{k}'] = v

    # prepend org attrs with org_
    for k, v in org.as_dict().items():
        # key exclusions
        if k not in ['id', 'jwt_aud', 'jwt_secret']:
            extras[f'org_{k}'] = v

    # merge role with user, with return dict sorted
    return dict(sorted({
        **user.as_dict(),
        **extras
    }.items()))


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
        :return:                True if the user exists or False
        """
        with session_scope() as session:
            if isinstance(user_identifier, str):
                logger.info("user_identifier is a str so finding user by email")
                ret = session.query(exists().where(User.email == user_identifier)).scalar()
            elif isinstance(user_identifier, int):
                logger.info("user_identifier is an int so finding user by id")
                ret = session.query(exists().where(User.id == user_identifier)).scalar()
            else:
                raise ValueError(f"bad user_identifier, expected Union[str, int] got {type(user_identifier)}")

        return ret

    @staticmethod
    def get_user(user_identifier: typing.Union[str, int]) -> User:
        """
        Gets a user by their id or email
        :param user_identifier: The user id or email
        :raises ValueError:     If the user doesn't exist.
        :return:                The User
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
    def user_create(request: request, require_auth: bool = True) -> Response:
        """
        Creates a user from a request
        :param request:         The request object
        :param require_auth:    If request needs to have authorization (e.g. not if signing up)
        :return:                Response
        """
        def create_user(valid_user: User, req_user: User = None) -> Response:
            """
            Creates the user
            :param valid_user:  The validated user object
            :param req_user:    The user making the request, if it was an authenticated request.
            :return:            Response
            """
            with session_scope() as session:
                user = User(
                    org_id=valid_user.org_id,
                    email=valid_user.email,
                    first_name=valid_user.first_name,
                    last_name=valid_user.last_name,
                    password=valid_user.password,
                    role=valid_user.role_name,
                    job_title=valid_user.job_title
                )
                session.add(user)
            if req_user is not None:
                req_user.log(
                    operation=Operation.CREATE,
                    resource=Resource.USER,
                    resource_id=user.id
                )
            else:
                user.log(
                    operation=Operation.CREATE,
                    resource=Resource.USER,
                    resource_id=user.id
                )
            logger.info(f"created user {user.as_dict()}")
            return g_response("Successfully created user", 201)

        request_body = request.get_json()

        # validate user
        from app.Controllers import ValidationController
        valid_user = ValidationController.validate_create_user_request(request_body)

        # response is failure, User object is a pass
        if isinstance(valid_user, Response):
            return valid_user

        if require_auth:
            logger.info("requiring auth to create user")
            req_user = AuthController.authorize_request(
                request=request,
                operation=Operation.CREATE,
                resource=Resource.USER,
                resource_org_id=valid_user.org_id
            )
            if isinstance(req_user, Response):
                return req_user
            elif isinstance(req_user, User):
                return create_user(valid_user, req_user=req_user)
        else:
            logger.info("not requiring auth to create user")
            return create_user(valid_user)

    @staticmethod
    def user_update(user_id: int, request: request) -> Response:
        """
        Updates a user, requires the full user object in the response body.
        :param user_id   The user id
        :param request:     The request object
        :return:            Response
        """
        from app.Controllers import ValidationController

        request_body = request.get_json()

        try:
            user_id = int(user_id)
        except ValueError:
            return g_response(f"cannot cast `{user_id}` to int", 400)

        valid_user = ValidationController.validate_update_user_request(user_id, request_body)

        if isinstance(valid_user, Response):
            return valid_user
        else:
            req_user = AuthController.authorize_request(
                request=request,
                operation=Operation.UPDATE,
                resource=Resource.USER,
                resource_org_id=valid_user.org_id,
                resource_user_id=user_id
            )
            if isinstance(req_user, Response):
                return req_user
            elif isinstance(req_user, User):
                user_to_update = UserController.get_user_by_id(user_id)

                with session_scope():
                    for prop, val in valid_user:
                        user_to_update.__setattr__(prop, val)

                req_user.log(
                    operation=Operation.UPDATE,
                    resource=Resource.USER,
                    resource_id=user_id
                )
                logger.info(f"updated user {user_to_update.as_dict()}")
                return g_response(status=204)

    @staticmethod
    def user_get(user_identifier: typing.Union[int, str], request: request) -> Response:
        """
        Get a single user.
        :param user_identifier:     The user ID
        :param request:     The request object
        :return:
        """
        from app.Controllers import UserController

        # is the identifier an email or user_id?
        try:
            user_identifier = int(user_identifier)
            logger.info("user_identifier is an id")
        except ValueError as e:  # noqa
            from app.Controllers import ValidationController
            validate_identifier = ValidationController.validate_email(user_identifier)
            if isinstance(validate_identifier, Response):
                return validate_identifier
            else:
                user_identifier = str(user_identifier)
            logger.info("user_identifier is an email")

        # if user exists check if permissions are good and then return the user
        if UserController.user_exists(user_identifier):
            user = UserController.get_user(user_identifier)
            req_user = AuthController.authorize_request(
                request=request,
                operation=Operation.UPDATE,
                resource=Resource.USER,
                resource_user_id=user.id,
                resource_org_id=user.org_id
            )
            if isinstance(req_user, Response):
                return req_user
            elif isinstance(req_user, User):
                req_user.log(
                    operation=Operation.GET,
                    resource=Resource.USER,
                    resource_id=user.id
                )
                logger.info(f"got user {user.as_dict()}")
                return j_response(user.as_dict())
        else:
            logger.info(f"user with id {user_identifier} does not exist")
            return g_response("User does not exist.", 400)

    @staticmethod
    def user_get_all(request: request) -> Response:
        """
        Get all users
        :param request:     The request object
        :return:
        """
        from app.Controllers import AuthController
        from app.Models import User

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.GET,
            resource=Resource.USERS
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):

            with session_scope() as session:
                users_qry = session.query(User, Role, Organisation) \
                    .join(User.roles) \
                    .join(User.orgs) \
                    .filter(User.org_id == req_user.org_id) \
                    .all()

            users = [_make_user_dict(u, r, o) for u, r, o in users_qry]

            logger.info(f"retrieved {len(users)} users: {json.dumps(users)}")
            return j_response(users)

    @staticmethod
    def get_full_user_as_dict(user_id: int) -> typing.Union[dict, Response]:
        """
        Returns a full user object with all of its FK's joined.
        :param user_id: The user id
        :return:        A user
        """
        with session_scope() as session:
            user_qry = session.query(User, Role, Organisation)\
                            .join(User.roles)\
                            .join(User.orgs)\
                            .filter(User.id == user_id)\
                            .all()
            if user_qry is not None:
                user_dict = {}
                for u, r, o in user_qry:
                    user_dict = _make_user_dict(u, r, o)
                return user_dict
            else:
                return g_response("Couldn't find user with id {user_id}", 400)

    @staticmethod
    def user_pages(_request: request) -> Response:
        """
        Returns the pages a user can access
        :param _request: The request
        :return: A response with a list of pages
        """
        from app.Controllers import AuthController

        req_user = AuthController.authorize_request(
            request=_request,
            operation=Operation.GET,
            resource=Resource.PAGES
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            with session_scope() as session:
                pages_qry = session.query(Permission.resource_id).filter(
                    Permission.role_id == req_user.role,
                    Permission.resource_id.like("%_PAGE")
                ).all()

                ret = []
                for permission in pages_qry:
                    for page in permission:
                        # strip _PAGE
                        ret.append(page.split('_PAGE')[0])

                return j_response(sorted(ret))
