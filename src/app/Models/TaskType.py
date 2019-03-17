from app import db


class TaskType(db.Model):
    __tablename__ = "task_types"

    id = db.Column('id', db.Integer, primary_key=True)
    label = db.Column('label', db.String)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    disabled = db.Column('disabled', db.Boolean, default=False)

    orgs = db.relationship("Organisation")

    def __init__(
            self,
            type: str,
            org_id: int,
            disabled: bool = False
    ):
        self.label = type
        self.org_id = org_id
        self.disabled = disabled

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskType object
        """
        return {
            "id": self.id,
            "type": self.label,
            "org_id": self.org_id,
            "disabled": self.disabled
        }
