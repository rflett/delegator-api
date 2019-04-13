import datetime
import typing
from app import db, session_scope
from app.Models import Organisation, User, TaskPriority, TaskType, TaskStatus  # noqa
from sqlalchemy.orm import aliased


def _get_fat_task(task_id: int) -> dict:
    """
    Creates a nice dict of a task
    """
    with session_scope() as session:
        task_assignee, task_created_by = aliased(User), aliased(User)
        tasks_qry = session.query(Task, task_assignee, task_created_by, TaskStatus, TaskType, TaskPriority) \
            .outerjoin(task_assignee, task_assignee.id == Task.assignee) \
            .join(task_created_by, task_created_by.id == Task.created_by) \
            .join(Task.created_bys) \
            .join(Task.task_statuses) \
            .join(Task.task_types) \
            .join(Task.task_priorities) \
            .filter(Task.id == task_id) \
            .first()

    t, ta, tcb, ts, tt, tp = tasks_qry

    extras = {
        'assignee': ta.as_dict() if ta is not None else None,
        'created_by': tcb.as_dict(),
        'status': ts.as_dict(),
        'type': tt.fat_dict(),
        'priority': tp.as_dict()
    }

    task_dict = t.as_dict()

    # remove extras from base task
    for k in extras:
        task_dict.pop(k)

    # convert datetimes to str
    for k, v in task_dict.items():
        if isinstance(v, datetime.datetime):
            task_dict[k] = v.strftime("%Y-%m-%d %H:%M:%S%z")

    return dict(sorted({
        **task_dict,
        **extras
    }.items()))


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column('id', db.Integer, primary_key=True)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    type = db.Column('type', db.Integer, db.ForeignKey('task_types.id'))
    description = db.Column('description', db.String)
    status = db.Column('status', db.String, db.ForeignKey('task_statuses.status'))
    time_estimate = db.Column('time_estimate', db.Integer, default=0)
    due_time = db.Column('due_time', db.DateTime)
    assignee = db.Column('assignee', db.Integer, db.ForeignKey('users.id'), default=None)
    priority = db.Column('priority', db.Integer, db.ForeignKey('task_priorities.priority'), default=1)
    created_by = db.Column('created_by', db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)
    finished_at = db.Column('finished_at', db.DateTime)
    status_changed_at = db.Column('status_changed_at', db.DateTime)
    priority_changed_at = db.Column('priority_changed_at', db.DateTime)

    orgs = db.relationship("Organisation")
    assignees = db.relationship("User", foreign_keys=[assignee])
    created_bys = db.relationship("User", foreign_keys=[created_by])
    task_statuses = db.relationship("TaskStatus")
    task_types = db.relationship("TaskType")
    task_priorities = db.relationship("TaskPriority")

    def __init__(
        self,
        org_id: int,
        type: int,
        description: str,
        status: str,
        time_estimate: int,
        due_time: datetime,
        assignee: typing.Optional[int],
        priority: int,
        created_by: int,
        created_at: datetime,
        finished_at: datetime,
        status_changed_at: datetime = None,
        priority_changed_at: datetime = None
    ):
        self.org_id = org_id
        self.type = type
        self.description = description
        self.status = status
        self.time_estimate = time_estimate
        self.due_time = due_time
        self.assignee = assignee
        self.priority = priority
        self.created_by = created_by
        self.created_at = created_at
        self.finished_at = finished_at
        self.status_changed_at = status_changed_at
        self.priority_changed_at = priority_changed_at

    def as_dict(self) -> dict:
        """
        :return: dict repr of a Task object
        """
        return {
            "id": self.id,
            "org_id": self.org_id,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "time_estimate": self.time_estimate,
            "due_time": self.due_time,
            "assignee": self.assignee,
            "priority": self.priority,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "status_changed_at": self.status_changed_at,
            "priority_changed_at": self.priority_changed_at
        }

    def fat_dict(self) -> dict:
        """ Returns a full task dict with all of its FK's joined. """
        return _get_fat_task(self.id)
