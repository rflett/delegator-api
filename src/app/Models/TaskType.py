from app import DBBase
from sqlalchemy import String, Column


class TaskType(DBBase):
    __tablename__ = "task_types"

    type = Column('type', String(), primary_key=True)

    def __init__(self, type: str):
        self.type = type

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TasktType object
        """
        return {
            "type": self.type
        }
