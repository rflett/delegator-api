from app import session_scope
from app.Models import User
from app.Exceptions import ResourceNotFoundError


class UserService(object):
    @staticmethod
    def get_by_id(user_id: int) -> User:
        """Retrieves a user by their id"""
        with session_scope() as session:
            user = session.query(User).filter_by(id=user_id, deleted=None).first()
        if user is None:
            raise ResourceNotFoundError(f"User with id {user_id} does not exist.")
        else:
            return user

    @staticmethod
    def get_by_email(email: str) -> User:
        """Retrieves a user by their email address"""
        with session_scope() as session:
            user = session.query(User).filter_by(email=email, deleted=None).first()
        if user is None:
            raise ResourceNotFoundError(f"User with email {email} does not exist.")
        else:
            return user
