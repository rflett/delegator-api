from app import DBSession
from app.Models import User
from app.Models.Enums import UserRole
from sqlalchemy import exists

session = DBSession()


class UserController(object):
    @staticmethod
    def create_user(
            org_id: int,
            username: str,
            email: str,
            first_name: str,
            last_name: str,
            password: str,
            role: UserRole
    ) -> None:
        """ Creates a user """
        user = User(
            org_id=org_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role=role
        )
        session.add(user)
        session.commit()

    @staticmethod
    def get_user_by_email(email: str) -> User:
        """ Gets a user by username """
        user_exists = session.query(exists().where(User.email == email)).scalar()
        if user_exists:
            return session.query(User).filter(User.email == email).first()
        else:
            raise ValueError(f"User with email {email} does not exist.")

    @staticmethod
    def get_user_by_username(username: str) -> User:
        """ Gets a user by username """
        user_exists = session.query(exists().where(User.username == username)).scalar()
        if user_exists:
            return session.query(User).filter(User.email == username).first()
        else:
            raise ValueError(f"User with username {username} does not exist.")
