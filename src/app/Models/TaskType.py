import datetime
import typing

from app import db, session_scope, app


def _get_fat_task_type(task_type) -> dict:
    """ Creates a nice dict of a task type """
    from app.Models import TaskTypeEscalation
    task_type_dict = task_type.as_dict()

    # get task type escalations
    with session_scope() as session:
        tte_qry = session.query(TaskTypeEscalation).filter(TaskTypeEscalation.task_type_id == task_type.id).all()
        escalation_policies = [escalation.as_dict() for escalation in tte_qry]

    # sort by display order
    task_type_dict['escalation_policies'] = list(sorted(escalation_policies, key=lambda i: i['display_order']))

    return task_type_dict


class TaskType(db.Model):
    __tablename__ = "task_types"

    id = db.Column('id', db.Integer, primary_key=True)
    label = db.Column('label', db.String)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    disabled = db.Column('disabled', db.DateTime, default=None)

    orgs = db.relationship("Organisation")

    def __init__(
            self,
            label: str,
            org_id: int,
            disabled: typing.Union[datetime.datetime, None] = None
    ):
        self.label = label
        self.org_id = org_id
        self.disabled = disabled

    def as_dict(self) -> dict:
        """
        :return: dict repr of a TaskType object
        """
        if self.disabled is None:
            disabled = None
        else:
            disabled = self.disabled.strftime(app.config['RESPONSE_DATE_FORMAT'])

        return {
            "id": self.id,
            "label": self.label,
            "org_id": self.org_id,
            "disabled": disabled
        }

    def fat_dict(self) -> dict:
        return _get_fat_task_type(self)
