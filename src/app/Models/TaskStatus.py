from app import db
from sqlalchemy import String, Column


class TaskStatus(db.Model):
    __tablename__ = "task_statuses"

    status = Column('status', String(), primary_key=True)
    label = Column('label', String(), default=None)

    def __init__(
            self,
            status: str,
            label: str
    ):
        self.status = status
        self.label = label

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskStatus object
        """
        return {
            "status": self.status,
            "label": self.label
        }
