import datetime

from app.Extensions.Database import db


class Operation(db.Model):
    __tablename__ = "rbac_operations"

    id = db.Column("id", db.String, primary_key=True)
    name = db.Column("name", db.String, nullable=False)
    description = db.Column("description", db.String)
    created_at = db.Column("created_at", db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, id: str, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description

    def as_dict(self) -> dict:
        """
        :return: The dict repr of an Operation object
        """
        return {"id": self.id, "name": self.name, "description": self.description}
