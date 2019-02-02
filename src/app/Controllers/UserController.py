import typing
from app import DBSession, logger
from app.Controllers import AuthController, ValidationController
from app.Models import User
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists

session = DBSession()


def _user_exists(user_identifier: typing.Union[int, str]) -> bool:
    """
    Checks to see if an org exists

    :param user_identifier: The org id or name

    :return: True if the org exists or False
    """
    if isinstance(user_identifier, str):
        logger.debug("user_identifier is a str so finding user by email")
        return session.query(exists().where(User.email == user_identifier)).scalar()
    elif isinstance(user_identifier, int):
        logger.debug("user_identifier is an int so finding user by id")
        return session.query(exists().where(User.id == user_identifier)).scalar()


class UserController(object):
    @staticmethod
    def user_exists(user_identifier: typing.Union[str, int]):
        """
        Checks to see if a user exists

        :param user_identifier: The user id or email

        :return: True if the user exists or False
        """
        return _user_exists(user_identifier)
        
    @staticmethod
    def get_user_by_email(email: str) -> User:
        """ 
        Gets a user by their email address 
        
        :param emails str: The user's email
        :raises ValueError: If the user doesn't exist.

        :return: The User
        """
        if _user_exists(email):
            return session.query(User).filter(User.email == email).first()
        else:
            raise ValueError(f"User with email {email} does not exist.")

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """
        Gets a user by their id

        :param id str: The user's id
        :raises ValueError: If the user doesn't exist.

        :return: The User
        """
        if _user_exists(user_id):
            return session.query(User).filter(User.id == user_id).first()
        else:
            raise ValueError(f"User with id {id} does not exist.")

    @staticmethod
    def user_create(request: request, require_auth: bool = True) -> Response:
        """
        Creates a user from a request

        :param request: The request object
        :param require_auth: If request needs to have authoriziation (e.g. not if signing up)
        :return: Response
        """
        def create_user(request_body: dict, req_user: User = None) -> Response:
            """
            Creates the user

            :param request_body: Request body
            :param req_user: The user making the request, if it was an authenticated request.
            :return: Response
            """
            from app.Controllers import ValidationController
            check_request = ValidationController.validate_create_user_request(request_body)
            if isinstance(check_request, Response):
                return check_request
            else:
                # check that user being created is for the same org as the user making the request
                # unless they're an admin
                if isinstance(req_user, User):
                    if req_user.org_id != check_request.org_id and req_user.role != 'ADMIN':
                        logger.debug(f"user {req_user.id} with role {req_user.role} attempted to create a user under "
                                     f"org {check_request.org_id} when their org is {req_user.id}")
                        return Response("Cannot create user for org that is not your own", 403)
                    else:
                        logger.debug(f"user {req_user.id} with role {req_user.role} can create a user under "
                                     f"org {check_request.org_id} when their org is {req_user.id}")

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
                logger.debug(f"created user {user.as_dict()}")
                return Response("Successfully created user", 200)

        if require_auth:
            logger.debug("requiring auth to create user")
            req_user = AuthController.authorize_request(request, Operation.CREATE, Resource.USER)
            if isinstance(req_user, Response):
                return req_user
            elif isinstance(req_user, User):
                req_user.log(Operation.CREATE, Resource.USER)
                return create_user(request.get_json(), req_user=req_user)
        else:
            logger.debug("not requiring auth to create user")
            return create_user(request.get_json())
