from app import DBSession
from app.Models import User
from app.Models.LogModels import RBACAuditLog

session = DBSession()


class RBACAuditLogController(object):
    @staticmethod
    def log(user: User, operation: str, resource: str) -> None:
        """
        Logs an action that a user would perform.
        
        :param user User:       The user to log the action against.
        :param operation str:   The operation performed.
        :param resource str:    The resource affected
        """
        audit_log = RBACAuditLog(
            org_id=user.org_id,
            user_id=user.id,
            operation=operation,
            resource=resource
        )
        session.add(audit_log)
        session.commit()
