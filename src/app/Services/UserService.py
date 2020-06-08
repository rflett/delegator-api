import typing

from sqlalchemy import and_
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ResourceNotFoundError
from app.Models.Dao import User


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
    def get_all_user_ids(org_id: int, exclude: list = None) -> typing.List[int]:
        """Returns a list of all user ids in an org"""
        if exclude is None:
            exclude = []

        with session_scope() as session:
            user_ids_qry = session.query(User.id).filter(and_(User.org_id == org_id, User.id.notin_(exclude)))

        return [user_id[0] for user_id in user_ids_qry]
