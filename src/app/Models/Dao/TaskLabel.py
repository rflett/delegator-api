from app.Extensions.Database import db


class TaskLabel(db.Model):
    __tablename__ = "task_labels"

    id = db.Column("id", db.Integer, primary_key=True)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    label = db.Column("label", db.String)
    colour = db.Column("colour", db.String, default=None)

    def __init__(
        self,
        org_id: int,
        label: str,
        colour: str = None,
    ):
        self.org_id = org_id
        self.label = label
        self.colour = colour

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskLabel object
        """
        return {"id": self.id, "label": self.label, "colour": self.colour}
