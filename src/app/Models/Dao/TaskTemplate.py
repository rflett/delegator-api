import datetime
import pytz
import typing

from flask import current_app

from app.Extensions.Database import db


class TaskTemplate(db.Model):
    __tablename__ = "task_templates"

    id = db.Column("id", db.Integer, primary_key=True)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    disabled = db.Column("disabled", db.DateTime, default=None)
    title = db.Column("title", db.String)
    default_time_estimate = db.Column("default_time_estimate", db.Integer, default=-1)
    default_priority = db.Column("default_priority", db.Integer, db.ForeignKey("task_priorities.priority"), default=-1)
    default_description = db.Column("default_description", db.String, default="")
    escalations = db.relationship("TaskTemplateEscalation", lazy=True)
    label_1 = db.Column("label_1", db.Integer, default=None)
    label_2 = db.Column("label_2", db.Integer, default=None)
    label_3 = db.Column("label_3", db.Integer, default=None)

    def __init__(
        self,
        org_id: int,
        title: str,
        disabled: typing.Union[datetime.datetime, None] = None,
        default_time_estimate: int = -1,
        default_description: str = None,
        default_priority: int = -1,
        label_1: int = None,
        label_2: int = None,
        label_3: int = None,
    ):
        self.title = title
        self.org_id = org_id
        self.disabled = disabled
        self.default_description = default_description
        self.default_priority = default_priority
        self.default_time_estimate = default_time_estimate
        self.label_1 = label_1
        self.label_2 = label_2
        self.label_3 = label_3

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskType object
        """
        if self.disabled is None:
            disabled = None
        else:
            disabled = pytz.utc.localize(self.disabled)
            disabled = disabled.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        return {
            "id": self.id,
            "org_id": self.org_id,
            "title": self.title,
            "disabled": disabled,
            "tooltip": "Type has been disabled" if disabled else None,
            "default_description": self.default_description,
            "default_priority": self.default_priority,
            "default_time_estimate": self.default_time_estimate,
            "labels": [l for l in [self.label_1, self.label_2, self.label_3] if l is not None],
        }
