from app import DBSession
from app.Models import User
from app.Models.LogModels import RBACAuditLog

session = DBSession()


class RBACAuditLogController(object):
    @staticmethod
    def log(user: User, operation: str, resource: str) -> None:
        audit_log = RBACAuditLog(
            org_id=user.org_id,
            user_id=user.id,
            operation=operation,
            resource=resource
        )
        session.add(audit_log)
        session.commit()
