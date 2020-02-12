import typing

from sqlalchemy import func

from app.Extensions.Database import session_scope
from app.Extensions.Errors import  ResourceNotFoundError
from app.Models import User
from app.Models.Enums import Roles


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

    @staticmethod
    def get_all_user_ids(org_id: int) -> typing.List[int]:
        """Returns a list of all user ids in an org"""
        with session_scope() as session:
            user_ids_qry = session.query(User.id).filter_by(org_id=org_id).all()

        return [user_id[0] for user_id in user_ids_qry]

    @staticmethod
    def is_user_only_org_admin(user: User) -> bool:
        """Checks to see if the user is the only ORG_ADMIN"""
        if user.role != Roles.ORG_ADMIN:
            return False

        with session_scope() as session:
            org_admins_cnt = (
                session.query(func.count(User.id))
                .filter(
                    User.role == Roles.ORG_ADMIN,
                    User.org_id == user.org_id,
                    User.disabled == None,  # noqa
                    User.deleted == None,  # noqa
                )
                .scalar()
            )

        return True if org_admins_cnt == 1 else False
