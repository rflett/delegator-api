import datetime

from app import db


class Role(db.Model):
    __tablename__ = "rbac_roles"

    id = db.Column('id', db.String, primary_key=True)
    rank = db.Column('rank', db.Integer)
    name = db.Column('name', db.String)
    description = db.Column('description', db.String, default=None)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            id: str,
            rank: int,
            name: str,
            description: str
    ):
        self.id = id
        self.rank = rank
        self.name = name
        self.description = description

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a Role object
        """
        return {
            "id":  self.id,
            "rank": self.rank,
            "name": self.name,
            "description": self.description
        }
