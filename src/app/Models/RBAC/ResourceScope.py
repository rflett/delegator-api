import datetime
from app import db
from sqlalchemy import Column, String, DateTime

SELF = 'SELF'
ORG = 'ORG'
GLOBAL = 'GLOBAL'


class ResourceScope(db.Model):
    __tablename__ = "rbac_resource_scopes"

    id = db.Column('id', db.String, primary_key=True)
    name = db.Column('name', db.String, nullable=False)
    description = db.Column('description', db.String)
    created_at = db.Column('created_at', DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            id: str,
            name: str,
            description: str
    ):
        self.id = id
        self.name = name
        self.description = description

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a Resource object
        """
        return {
            "id":  self.id,
            "name": self.name,
            "description": self.description
        }
