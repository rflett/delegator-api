from app.Extensions.Database import db


class TaskTemplateEscalation(db.Model):
    __tablename__ = "task_template_escalations"

    id = db.Column("id", db.Integer, primary_key=True)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    template_id = db.Column("template_id", db.Integer, db.ForeignKey("task_templates.id"))
    delay = db.Column(
        "delay",
        db.Integer,
    )
    from_priority = db.Column("from_priority", db.Integer, db.ForeignKey("task_priorities.priority"))
    to_priority = db.Column("to_priority", db.Integer, db.ForeignKey("task_priorities.priority"))

    def __init__(self, org_id: int, template_id: int, delay: int, from_priority: int, to_priority: int):
        self.org_id = org_id
        self.template_id = template_id
        self.delay = delay
        self.from_priority = from_priority
        self.to_priority = to_priority

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskTemplateEscalation object
        """
        return {
            "id": self.id,
            "org_id": self.org_id,
            "template_id": self.template_id,
            "delay": self.delay,
            "from_priority": self.from_priority,
            "to_priority": self.to_priority,
        }
