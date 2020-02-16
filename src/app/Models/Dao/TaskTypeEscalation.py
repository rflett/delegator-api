from app.Extensions.Database import db


class TaskTypeEscalation(db.Model):
    __tablename__ = "task_type_escalations"

    task_type_id = db.Column("task_type_id", db.Integer, db.ForeignKey("task_types.id"), primary_key=True)
    display_order = db.Column("display_order", db.Integer, primary_key=True)
    delay = db.Column("delay", db.Integer,)
    from_priority = db.Column("from_priority", db.Integer, db.ForeignKey("task_priorities.priority"))
    to_priority = db.Column("to_priority", db.Integer, db.ForeignKey("task_priorities.priority"))

    task_type = db.relationship("TaskType")
    from_priorities = db.relationship("TaskPriority", foreign_keys=[from_priority])
    to_priorities = db.relationship("TaskPriority", foreign_keys=[to_priority])

    def __init__(self, task_type_id: int, display_order: int, delay: int, from_priority: int, to_priority: int):
        self.task_type_id = task_type_id
        self.display_order = display_order
        self.delay = delay
        self.from_priority = from_priority
        self.to_priority = to_priority

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskTypeEscalation object
        """
        return {
            "task_type_id": self.task_type_id,
            "display_order": self.display_order,
            "delay": self.delay,
            "from_priority": self.from_priority,
            "to_priority": self.to_priority,
        }
