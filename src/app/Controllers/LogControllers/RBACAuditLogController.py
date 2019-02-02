import json
import typing
from app import DBSession, logger
from app.Models import User
from app.Models.LogModels import RBACAuditLog

session = DBSession()


class RBACAuditLogController(object):
    @staticmethod
    def log(user: User, **kwargs) -> None:
        """
        Logs an action that a user would perform.
        
        :param user User:       The user to log the action against.
        :param operation str:   The operation performed.
        :param resource str:    The resource affected
        :param resource_id:     An optional resource id
        """
        audit_log = RBACAuditLog(
            org_id=user.org_id,
            user_id=user.id,
            **kwargs
        )
        session.add(audit_log)
        session.commit()
        logger.debug(f"logged op {kwargs.get('operation')} on res {kwargs.get('resource')} "
                     f"with id {kwargs.get('resource_id')} against user {user.id}")
