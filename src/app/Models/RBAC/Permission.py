import datetime
from app import DBBase
from app.Models.RBAC import Operation, Resource, ResourceScope # noqa
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship


class Permission(DBBase):
    __tablename__ = "rbac_permissions"

    role_id = Column('role_id', String(), primary_key=True)
    operation_id = Column('operation_id', String(), ForeignKey('rbac_operations.id'), primary_key=True)
    resource_id = Column('resource_id', String(), ForeignKey('rbac_resources.id'), primary_key=True)
    resource_scope = Column('resource_scope', String(), ForeignKey('rbac_resource_scopes.id'), primary_key=True)
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    operations = relationship("Operation")
    resources = relationship("Resource")
    resource_scopes = relationship("ResourceScope")

    def __init__(
            self,
            role_id: str,
            operation_id: str,
            resource_id: str,
            resource_scope: str
    ):
        self.role_id = role_id
        self.operation_id = operation_id
        self.resource_id = resource_id
        self.resource_scope = resource_scope

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a Permission object
        """
        return {
            "role_id":  self.role_id,
            "operation_id": self.operation_id,
            "resource_id": self.resource_id,
            "resource_scope": self.resource_scope
        }
