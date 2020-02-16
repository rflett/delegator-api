import datetime
import typing

from flask import current_app

from app.Extensions.Database import db, session_scope


class TaskType(db.Model):
    __tablename__ = "task_types"

    id = db.Column("id", db.Integer, primary_key=True)
    label = db.Column("label", db.String)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    disabled = db.Column("disabled", db.DateTime, default=None)
    default_time_estimate = db.Column("default_time_estimate", db.Integer, default=-1)
    default_priority = db.Column("default_priority", db.Integer, db.ForeignKey("task_priorities.priority"), default=-1)
    default_description = db.Column("default_description", db.String)

    orgs = db.relationship("Organisation")

    def __init__(
        self,
        label: str,
        org_id: int,
        disabled: typing.Union[datetime.datetime, None] = None,
        default_time_estimate: int = -1,
        default_description: str = None,
        default_priority: int = -1,
    ):
        self.label = label
        self.org_id = org_id
        self.disabled = disabled
        self.default_description = default_description
        self.default_priority = default_priority
        self.default_time_estimate = default_time_estimate

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskType object
        """
        if self.disabled is None:
            disabled = None
        else:
            disabled = self.disabled.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        return {
            "id": self.id,
            "label": self.label,
            "org_id": self.org_id,
            "disabled": disabled,
            "tooltip": "Type has been disabled" if disabled else None,
            "default_description": self.default_description,
            "default_priority": self.default_priority,
            "default_time_estimate": self.default_time_estimate,
        }

    def fat_dict(self) -> dict:
        from app.Models.Dao import TaskTypeEscalation

        task_type_dict = self.as_dict()

        # get task type escalations
        with session_scope() as session:
            tte_qry = session.query(TaskTypeEscalation).filter_by(task_type_id=self.id).all()
            escalation_policies = [escalation.as_dict() for escalation in tte_qry]

        # sort by display order
        task_type_dict["escalation_policies"] = list(sorted(escalation_policies, key=lambda i: i["display_order"]))

        return task_type_dict
