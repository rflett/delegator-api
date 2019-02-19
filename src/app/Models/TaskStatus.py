from app import DBBase
from sqlalchemy import String, Column


class TaskStatus(DBBase):
    __tablename__ = "task_statuses"

    status = Column('status', String(), primary_key=True)

    def __init__(self, status: str):
        self.status = status

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskStatus object
        """
        return {
            "status": self.status
        }
