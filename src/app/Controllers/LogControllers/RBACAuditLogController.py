from app import logger, session_scope
from app.Models import User
from app.Models.LogModels import RBACAuditLog


class RBACAuditLogController(object):
    @staticmethod
    def log(user: User, **kwargs) -> None:
        """
        Logs an action that a user would perform.
        :param user:    The user to log the action against.
        :param kwargs:  operation, resource, optional(resource_id)
        """
        audit_log = RBACAuditLog(
            org_id=user.org_id,
            user_id=user.id,
            **kwargs
        )
        with session_scope() as session:
            session.add(audit_log)
        logger.debug(f"logged op {kwargs.get('operation')} on res {kwargs.get('resource')} "
                     f"with id {kwargs.get('resource_id')} against user {user.id}")
