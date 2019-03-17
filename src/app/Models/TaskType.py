from app import db
from app.Models import Organisation  # noqa
from sqlalchemy import String, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship


class TaskType(db.Model):
    __tablename__ = "task_types"

    id = db.Column('id', db.Integer, primary_key=True)
    label = db.Column('label', db.String)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))

    orgs = db.relationship("Organisation")

    def __init__(self, type: str, org_id: int):
        self.label = type
        self.org_id = org_id

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TasktType object
        """
        return {
            "type": self.label,
            "org_id": self.org_id
        }
