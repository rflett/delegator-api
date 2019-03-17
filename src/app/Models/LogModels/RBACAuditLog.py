import datetime
from app import db
from app.Models import Organisation, User   # noqa
from app.Models.RBAC import Resource, Operation   # noqa
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship


class RBACAuditLog(db.Model):
    __tablename__ = "rbac_audit_log"

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
    operation = db.Column('operation', db.String, db.ForeignKey('rbac_operations.id'))
    resource = db.Column('resource', db.String, db.ForeignKey('rbac_resources.id'))
    resource_id = db.Column('resource_id', db.Integer, default=None)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)

    orgs = db.relationship("Organisation")
    users = db.relationship("User")
    operations = db.relationship("Operation")
    resources = db.relationship("Resource")

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
        """
        :return: The dict repr of an RBACAuditLog object
        """
        return {
            'org_id': self.org_id,
            'user_id': self.user_id,
            'operation': self.operation,
            'resource': self.resource,
            'resource_id': self.resource_id
        }
