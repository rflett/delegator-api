from app import DBSession
from app.Models import User
from app.Models.Enums import UserRole

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
    def get_user_by_username(username: str) -> User:
        """ Gets a user by username """
        return session.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_email(email: str) -> User:
        """ Gets a user by username """
        return session.query(User).filter(User.email == email).first()
