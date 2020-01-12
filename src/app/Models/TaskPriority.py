from app import db


class TaskPriority(db.Model):
    __tablename__ = "task_priorities"

    priority = db.Column("priority", db.Integer, primary_key=True)
    label = db.Column("label", db.String, default=None)

    def __init__(self, priority: int, label: str):
        self.priority = priority
        self.label = label

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskPriority object
        """
        return {"priority": self.priority, "label": self.label}
