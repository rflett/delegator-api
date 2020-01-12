import datetime

from app import db
from app.Models.RBAC import Operation, Resource, ResourceScope  # noqa


class Permission(db.Model):
    __tablename__ = "rbac_permissions"

    role_id = db.Column("role_id", db.String, primary_key=True)
    operation_id = db.Column("operation_id", db.String, db.ForeignKey("rbac_operations.id"), primary_key=True)
    resource_id = db.Column("resource_id", db.String, db.ForeignKey("rbac_resources.id"), primary_key=True)
    resource_scope = db.Column("resource_scope", db.String, db.ForeignKey("rbac_resource_scopes.id"), primary_key=True)
    created_at = db.Column("created_at", db.DateTime, default=datetime.datetime.utcnow)

    operations = db.relationship("Operation")
    resources = db.relationship("Resource")
    resource_scopes = db.relationship("ResourceScope")

    def __init__(self, role_id: str, operation_id: str, resource_id: str, resource_scope: str):
        self.role_id = role_id
        self.operation_id = operation_id
        self.resource_id = resource_id
        self.resource_scope = resource_scope

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a Permission object
        """
        return {
            "role_id": self.role_id,
            "operation_id": self.operation_id,
            "resource_id": self.resource_id,
            "resource_scope": self.resource_scope,
        }
