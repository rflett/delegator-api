from app import DBSession
from app.Models import User

session = DBSession()


class UserController(object):
    @staticmethod
    def get_user(username: str, password: str) -> User:
        try:
            user = session.query(User).filter(User.username == username).first()
            return user.get_auth_data()
        except Exception as e:
            pass
