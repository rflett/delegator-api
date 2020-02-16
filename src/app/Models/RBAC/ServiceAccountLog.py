import datetime
import typing

from app.Extensions.Database import db


class ServiceAccountLog(db.Model):
    __tablename__ = "rbac_sa_audit_log"

    id = db.Column("id", db.Integer, primary_key=True, autoincrement=True)
    account_name = db.Column("account_name", db.String)
    operation = db.Column("operation", db.String, db.ForeignKey("rbac_operations.id"))
    resource = db.Column("resource", db.String, db.ForeignKey("rbac_resources.id"))
    resource_id = db.Column("resource_id", db.Integer, default=None)
    created_at = db.Column("created_at", db.DateTime, default=datetime.datetime.utcnow)

    operations = db.relationship("Operation")
    resources = db.relationship("Resource")

    def __init__(self, account_name: str, operation: str, resource: str, resource_id: typing.Union[int, None] = None):
        self.account_name = account_name
        self.operation = operation
        self.resource = resource
        self.resource_id = resource_id

    def to_dict(self) -> dict:
        """
        :return: The dict repr of an RBACServiceAccountAuditLog object
        """
        return {
            "account_name": self.account_name,
            "operation": self.operation,
            "resource": self.resource,
            "resource_id": self.resource_id,
        }
