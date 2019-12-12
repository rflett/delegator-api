import typing
from app import db


class TaskStatus(db.Model):
    __tablename__ = "task_statuses"

    status = db.Column('status', db.String, primary_key=True)
    label = db.Column('label', db.String, default=None)

    def __init__(
            self,
            status: str,
            label: str
    ):
        self.status = status
        self.label = label

    def as_dict(self, disabled: bool = False, tooltip: typing.Union[str, None] = None) -> dict:
        """
        :return: dict repr of a TaskStatus object
        """
        return {
            "status": self.status,
            "label": self.label,
            "disabled": disabled,
            "tooltip": tooltip
        }