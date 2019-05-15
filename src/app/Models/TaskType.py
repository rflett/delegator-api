from app import db, session_scope


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

    def fat_dict(self) -> dict:
        return _get_fat_task_type(self)
