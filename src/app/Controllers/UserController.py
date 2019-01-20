from app import DBSession
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
    def get_user_by_username(username: str) -> User:
        """ 
        Gets a user by their username 
        
        :param emails str: The user's username
        :raises ValueError: If the user doesn't exist.

        :return: The User
        """
        user_exists = session.query(exists().where(User.username == username)).scalar()
        if user_exists:
            return session.query(User).filter(User.username == username).first()
        else:
            raise ValueError(f"User with username {username} does not exist.")
