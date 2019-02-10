import json
import typing
from app import logger, g_response, session_scope
from app.Controllers import AuthController, ValidationController
from app.Models import User
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists


def _user_exists(user_identifier: typing.Union[int, str]) -> bool:
    """
    Checks to see if a user exists
    :param user_identifier: The user id or email
    :return:                True if the user exists or False
    """
    if isinstance(user_identifier, str):
        logger.debug("user_identifier is a str so finding user by email")
        with session_scope() as session:
            ret = session.query(exists().where(User.email == user_identifier)).scalar()
            return ret
    elif isinstance(user_identifier, int):
        logger.debug("user_identifier is an int so finding user by id")
        with session_scope() as session:
            ret = session.query(exists().where(User.id == user_identifier)).scalar()
            return ret


def _compare_user_orgs(user_resource: User, request_user: User) -> bool:
    """
    Checks to see if the user making the request belongs to the same organisation as the user they're
    affecting. The exception to this rule is for the global superuser account.
    :param user_resource:   The user affected by the request_user
    :param request_user:    The user making the request
    :return:                True if the orgs are equal or false
    """
    return True if request_user.org_id == user_resource.org_id or request_user.role == 'ADMIN' else False


class UserController(object):
    @staticmethod
    def user_exists(user_identifier: typing.Union[str, int]) -> bool:
        """
        Checks to see if a user exists
        :param user_identifier: The user id or email
        :return:                True if the user exists or False
        """
        return _user_exists(user_identifier)

    @staticmethod
    def get_user(user_identifier: typing.Union[str, int]) -> User:
        """
        Gets a user by their id or email
        :param user_identifier: The user id or email
        :raises ValueError:     If the user doesn't exist.
        :return:                The User
        """
        if _user_exists(user_identifier):
            if isinstance(user_identifier, str):
                logger.debug("user_identifier is a str so finding user by email")
                with session_scope() as session:
                    ret = session.query(User).filter(User.email == user_identifier).first()
                    return ret
            elif isinstance(user_identifier, int):
                logger.debug("user_identifier is an int so finding user by id")
                with session_scope() as session:
                    ret = session.query(User).filter(User.id == user_identifier).first()
                    return ret
        else:
            logger.debug(f"User with identifier {user_identifier} does not exist.")
            raise ValueError(f"User with identifier {user_identifier} does not exist.")

    @staticmethod
    def get_user_by_email(email: str) -> User:
        """
        Gets a user by their email address
        :param email:          The user's email
        :raises ValueError:     If the user doesn't exist.
        :return:                The User
        """
        if _user_exists(email):
            logger.debug(f"user {email} exists")
            with session_scope() as session:
                ret = session.query(User).filter(User.email == email).first()
                return ret
        else:
            logger.debug(f"User with email {email} does not exist.")
            raise ValueError(f"User with email {email} does not exist.")

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """
        Gets a user by their id
        :param user_id:              The user's id
        :raises ValueError:     If the user doesn't exist.
        :return:                The User
        """
        if _user_exists(user_id):
            logger.debug(f"user with id {user_id} exists")
            with session_scope() as session:
                ret = session.query(User).filter(User.id == user_id).first()
                return ret
        else:
            logger.debug(f"User with id {user_id} does not exist.")
            raise ValueError(f"User with id {user_id} does not exist.")

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
                    role=valid_user.role_name
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
                logger.debug(f"created user {user.as_dict()}")
                return g_response("Successfully created user", 201)

        request_body = request.get_json()

        # validate user
        from app.Controllers import ValidationController
        valid_user = ValidationController.validate_create_user_request(request_body)

        # response is failure, User object is a pass
        if isinstance(valid_user, Response):
            return valid_user

        if require_auth:
            logger.debug("requiring auth to create user")
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
            logger.debug("not requiring auth to create user")
            return create_user(valid_user)

    @staticmethod
    def user_update(request: request) -> Response:
        """
        Updates a user, requires the full user object in the response body.
        :param request: The request object
        :return:        Response
        """
        from app.Controllers import ValidationController

        request_body = request.get_json()
        valid_user = ValidationController.validate_update_user_request(request_body)

        if isinstance(valid_user, Response):
            return valid_user
        else:
            req_user = AuthController.authorize_request(
                request=request,
                operation=Operation.UPDATE,
                resource=Resource.USER,
                resource_org_id=valid_user.org_id,
                resource_user_id=valid_user.id
            )
            if isinstance(req_user, Response):
                return req_user
            elif isinstance(req_user, User):
                user_to_update = UserController.get_user_by_id(valid_user.id)

                with session_scope() as session:
                    for prop, val in valid_user:
                        user_to_update.__setattr__(prop, val)

                    req_user.log(
                        operation=Operation.UPDATE,
                        resource=Resource.USER,
                        resource_id=user_to_update.id
                    )
                    logger.debug(f"updated user {user_to_update.as_dict()}")
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
            logger.debug("user_identifier is an id")
        except ValueError as e:
            from app.Controllers import ValidationController
            validate_identifier = ValidationController.validate_email(user_identifier)
            if isinstance(validate_identifier, Response):
                return validate_identifier
            else:
                user_identifier = str(user_identifier)
            logger.debug("user_identifier is an email")

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
                logger.debug(f"got user {user.as_dict()}")
                return Response(json.dumps(user.as_dict()), headers={'Content-Type': 'application/json'})
        else:
            logger.debug(f"user with id {user_identifier} does not exist")
            return g_response("User does not exist.", 400)
