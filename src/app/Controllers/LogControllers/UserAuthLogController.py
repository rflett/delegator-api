import typing
from app import DBSession
from app.Models import User
from app.Models.LogModels import UserAuthLog

session = DBSession()


class UserAuthLogController(object):
    @staticmethod
    def log(user: User, action: str, action_detail: typing.Optional[str] = None) -> None:
        auth_log = UserAuthLog(
            org_id=user.org_id,
            user_id=user.id,
            action=action,
            action_detail=action_detail
        )
        session.add(auth_log)
        session.commit()
