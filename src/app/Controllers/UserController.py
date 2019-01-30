from app import DBSession
from app.Controllers import AuthController, ValidationController
from app.Models import User
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists

session = DBSession()


class UserController(object):
    @staticmethod
    def get_user_by_email(email: str) -> User:
        """ 
        Gets a user by their email address 
        
        :param emails str: The user's email
        :raises ValueError: If the user doesn't exist.

        :return: The User
        """
        user_exists = session.query(exists().where(User.email == email)).scalar()
        if user_exists:
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
        user_exists = session.query(exists().where(User.id == user_id)).scalar()
        if user_exists:
            return session.query(User).filter(User.id == user_id).first()
        else:
            raise ValueError(f"User with id {id} does not exist.")

    @staticmethod
    def create_user(request: request) -> Response:
        """
        Creates a user from a request

        :param request: The request object
        :return: Response
        """
        from app.Controllers import ValidationController
        req_user = AuthController.authorize_request(request, Operation.CREATE, Resource.USER)
        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            # create user
            request_body = request.get_json()
            check_request = ValidationController.validate_user_request(request_body)
            if isinstance(check_request, Response):
                return check_request
            else:
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

                req_user.log(Operation.CREATE, Resource.USER)

                return Response("Successfully created user", 200)
