import typing
from app import logger, session_scope
from app.Models import User
from app.Models.LogModels import UserAuthLog


class UserAuthLogController(object):
    @staticmethod
    def log(user: User, action: str, action_detail: typing.Optional[str] = None) -> None:
        """
        Logs user authentication activity in the database. Primarily used for login/logout/passwordreset.
        Other activities are tracked via the RBAC Audit Log.
        :param user:            The user to log the action against
        :param action:          The action (enum)
        :param action_detail:   More detail about the action
        :return:                None
        """
        auth_log = UserAuthLog(
            org_id=user.org_id,
            user_id=user.id,
            action=action,
            action_detail=action_detail
        )
        with session_scope() as session:
            session.add(auth_log)
        logger.info(f"user with id {user.id} has done {action}, details: {action_detail}")
