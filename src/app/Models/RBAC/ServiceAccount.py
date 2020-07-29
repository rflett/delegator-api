import typing
from dataclasses import dataclass

import structlog

from app.Extensions.Database import session_scope
from app.Extensions.Errors import AuthorizationError
from app.Models.RBAC import Permission

log = structlog.getLogger()


@dataclass
class ServiceAccount:
    """An account used by the other services which need to make authenticated calls to this API"""

    name: str

    def can(self, operation: str, resource: str) -> typing.Union[bool, str]:
        """
        Checks if service account can perform {operation} on {resource}.
        :param operation:   The operation to perform.
        :param resource:    The affected resource.
        :return:            True if they can do the thing, or False.
        """
        with session_scope() as session:
            permission = (
                session.query(Permission)
                .filter_by(role_id=self.name, operation_id=operation, resource_id=resource)
                .first()
            )

        if permission is None:
            raise AuthorizationError(f"No permissions to {operation} {resource}.")
        else:
            return permission.resource_scope

    def log(self, operation: str, resource: str, resource_id: typing.Union[int, None] = None) -> None:
        """
        Logs an action that a user would perform.
        """
        from app.Models.RBAC import ServiceAccountLog

        audit_log = ServiceAccountLog(
            account_name=self.name, operation=operation, resource=resource, resource_id=resource_id
        )
        with session_scope() as session:
            session.add(audit_log)
        log.info(f"service account {self.name} did {operation} on {resource} with " f"a resource_id of {resource_id}")
