import datetime
from app import DBBase
from sqlalchemy import Column, String, DateTime


class Permission(DBBase):
    __tablename__ = "rbac_permissions"

    role_id = Column('role_id', String(), primary_key=True)
    operation_id = Column('operation_id', String(), primary_key=True)
    resource_id = Column('resource_id', String(), primary_key=True)
    created_at = Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            role_id: str,
            operation_id: str,
            resource_id: str,
    ):
        self.role_id = role_id
        self.operation_id = operation_id
        self.resource_id = resource_id

    def as_dict(self) -> dict:
        """ Returns dict repr of Permission """
        return {
            "role_id":  self.role_id,
            "operation_id": self.operation_id,
            "resource_id": self.resource_id
        }
