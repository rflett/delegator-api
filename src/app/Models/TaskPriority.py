from app import db
from sqlalchemy import Integer, String, Column


class TaskPriority(db.Model):
    __tablename__ = "task_priorities"

    priority = Column('priority', Integer(), primary_key=True)
    label = Column('label', String(), default=None)

    def __init__(
        self,
        priority: int,
        label: str
    ):
        self.priority = priority
        self.label = label

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskPriority object
        """
        return {
            "priority": self.priority,
            "label": self.label
        }
