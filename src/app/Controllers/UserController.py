import json
import typing
from app import session, logger, g_response
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
        return session.query(exists().where(User.email == user_identifier)).scalar()
    elif isinstance(user_identifier, int):
        logger.debug("user_identifier is an int so finding user by id")
        return session.query(exists().where(User.id == user_identifier)).scalar()


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
                return session.query(User).filter(User.email == user_identifier).first()
            elif isinstance(user_identifier, int):
                logger.debug("user_identifier is an int so finding user by id")
                return session.query(User).filter(User.id == user_identifier).first()
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
            return session.query(User).filter(User.email == email).first()
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
            return session.query(User).filter(User.id == user_id).first()
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
        def create_user(request_body: dict, req_user: User = None) -> Response:
            """
            Creates the user
            :param request_body:    Request body
            :param req_user:        The user making the request, if it was an authenticated request.
            :return:                Response
            """
            from app.Controllers import ValidationController
            check_request = ValidationController.validate_create_user_request(request_body)
            if isinstance(check_request, Response):
                return check_request
            else:
                # check that user being created is for the same org as the user making the request
                # unless they're an admin
                if req_user is not None:
                    if _compare_user_orgs(check_request, req_user):
                        logger.debug(f"user {req_user.id} with role {req_user.role} can create a user under "
                                     f"org {check_request.org_id} when their org is {req_user.id}")
                    else:
                        logger.debug(f"user {req_user.id} with role {req_user.role} attempted to create a user under "
                                     f"org {check_request.org_id} when their org is {req_user.id}")
                        return g_response("Cannot create user for org that is not your own", 403)

                user = User(
                    org_id=check_request.org_id,
                    email=check_request.email,
                    first_name=check_request.first_name,
                    last_name=check_request.last_name,
                    password=check_request.password,
                    role=check_request.role_name
                )
                session.add(user)
                session.commit()
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
                return g_response("Successfully created user")

        if require_auth:
            logger.debug("requiring auth to create user")
            req_user = AuthController.authorize_request(request, Operation.CREATE, Resource.USER)
            if isinstance(req_user, Response):
                return req_user
            elif isinstance(req_user, User):
                return create_user(request.get_json(), req_user=req_user)
        else:
            logger.debug("not requiring auth to create user")
            return create_user(request.get_json())

    @staticmethod
    def user_update(request: request) -> Response:
        """
        Updates a user, requires the full user object in the response body.
        :param request: The request object
        :return:        Response
        """
        def update_user(request_body: dict, req_user: User) -> Response:
            """
            Updates the user
            :param request_body:    Request body
            :param req_user:        The user making the request
            :return:                Response
            """
            from app.Controllers import ValidationController
            check_request = ValidationController.validate_update_user_request(request_body)
            if isinstance(check_request, Response):
                return check_request
            else:
                # check that user being updated is for the same org as the user making the request
                # unless they're an admin
                if _compare_user_orgs(check_request, req_user):
                    logger.debug(f"user {req_user.id} with role {req_user.role} can update a user under "
                                 f"org {check_request.org_id} when their org is {req_user.id}")
                else:
                    logger.debug(f"user {req_user.id} with role {req_user.role} attempted to update a user under "
                                 f"org {check_request.org_id} when their org is {req_user.id}")
                    return g_response("Cannot update user for org that is not your own", 403)

                user_to_update = UserController.get_user_by_email(check_request.email)
                for prop, val in check_request:
                    user_to_update.__setattr__(prop, val)
                session.commit()

                req_user.log(
                    operation=Operation.UPDATE,
                    resource=Resource.USER,
                    resource_id=user_to_update.id
                )
                logger.debug(f"updated user {user_to_update.as_dict()}")
                return g_response(status=204)

        req_user = AuthController.authorize_request(request, Operation.UPDATE, Resource.USER)
        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            return update_user(request.get_json(), req_user)

    @staticmethod
    def user_get(user_identifier: typing.Union[int, str], request: request) -> Response:
        """
        Get a single user.
        :param user_identifier:     The user ID
        :param request:     The request object
        :return:
        """
        def get_user(identifier: typing.Union[int, str], req_user: User) -> Response:
            """
            Gets the user
            :param user_id:    The user id to GET
            :param req_user:   The user making the request
            :return:           Response
            """
            from app.Controllers import ValidationController, UserController
            check_request = ValidationController.validate_get_user_request(identifier)
            if isinstance(check_request, Response):
                return check_request
            else:
                user = UserController.get_user(identifier)
                if _compare_user_orgs(user, req_user):
                    logger.debug(f"user {req_user.id} with role {req_user.role} can get a user under "
                                 f"org {user.org_id} when their org is {req_user.id}")
                else:
                    logger.debug(f"user {req_user.id} with role {req_user.role} attempted to get a user under "
                                 f"org {user.org_id} when their org is {req_user.id}")
                    return g_response("Cannot get user for org that is not your own", 403)

            req_user.log(
                operation=Operation.GET,
                resource=Resource.USER,
                resource_id=user.id
            )
            logger.debug(f"got user {user.as_dict()}")
            return Response(json.dumps(user.as_dict()), headers={'Content-Type': 'application/json'})

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

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.UPDATE,
            resource=Resource.USER
        )
        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            return get_user(user_identifier, req_user)
