import datetime
import typing

from app.Extensions.Database import db


class Log(db.Model):
    __tablename__ = "rbac_audit_log"

    id = db.Column("id", db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    user_id = db.Column("user_id", db.Integer, db.ForeignKey("users.id"))
    operation = db.Column("operation", db.String, db.ForeignKey("rbac_operations.id"))
    resource = db.Column("resource", db.String, db.ForeignKey("rbac_resources.id"))
    resource_id = db.Column("resource_id", db.Integer, default=None)
    created_at = db.Column("created_at", db.DateTime, default=datetime.datetime.utcnow)

    orgs = db.relationship("Organisation")
    users = db.relationship("User")
    operations = db.relationship("Operation")
    resources = db.relationship("Resource")

    def __init__(
        self, org_id: int, user_id: int, operation: str, resource: str, resource_id: typing.Union[int, None] = None
    ):
        self.org_id = org_id
        self.user_id = user_id
        self.operation = operation
        self.resource = resource
        self.resource_id = resource_id

    def to_dict(self) -> dict:
        """
        :return: The dict repr of an RBACAuditLog object
        """
        return {
            "org_id": self.org_id,
            "user_id": self.user_id,
            "operation": self.operation,
            "resource": self.resource,
            "resource_id": self.resource_id,
        }
