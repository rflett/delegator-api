from app import db


class DelayedTask(db.Model):
    __tablename__ = "tasks_delayed"

    task_id = db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'), primary_key=True)
    delayed_until = db.Column('delayed_until', db.Integer)

    tasks = db.relationship("Task")

    def __init__(self, task_id: int, delayed_until: int):
        self.task_id = task_id
        self.delayed_until = delayed_until

    def as_dict(self):
        return {
            "task_id": self.task_id,
            "delayed_until": self.delayed_until
        }
