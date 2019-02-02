import datetime
import typing
from app import DBBase
from app.Models import Organisation, User
from app.Models.RBAC import Resource, Operation
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship


class RBACAuditLog(DBBase):
    __tablename__ = "rbac_audit_log"

    id = Column('id', Integer(), primary_key=True, autoincrement=True)
    org_id = Column('org_id', Integer(), ForeignKey('organisations.id'))
    user_id = Column('user_id', Integer(), ForeignKey('users.id'))
    operation = Column('operation', String(), ForeignKey('rbac_operations.id'))
    resource = Column('resource', String(), ForeignKey('rbac_resources.id'))
    resource_id = Column('resource_id', Integer(), default=None)
    created_at = Column('created_at', DateTime(), default=datetime.datetime.utcnow)

    r_org = relationship("Organisation")
    r_user = relationship("User")
    r_operation = relationship("Operation")
    r_resource = relationship("Resource")

    def __init__(
        self,
        org_id: int,
        user_id: int,
        **kwargs
    ):
        self.org_id = org_id
        self.user_id = user_id
        self.operation = kwargs.get('operation')
        self.resource = kwargs.get('resource')
        self.resource_id = kwargs.get('resource_id')

    def to_dict(self) -> dict:
        return {
            'org_id': self.org_id,
            'user_id': self.user_id,
            'operation': self.operation,
            'resource': self.resource,
            'resource_id': self.resource_id
        }
