import datetime

from boto3.dynamodb.conditions import Key
from sqlalchemy.orm import aliased

from app import db, session_scope, logger, task_activity_table, app
from app.Models import Organisation, User, TaskPriority, TaskType, TaskStatus  # noqa


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

    task_dict = t.as_dict()

    task_dict['assignee'] = ta.as_dict() if ta is not None else None
    task_dict['created_by'] = tcb.as_dict()
    task_dict['status'] = ts.as_dict()
    task_dict['type'] = tt.as_dict()
    task_dict['priority'] = tp.as_dict()

    return task_dict


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
    started_at = db.Column('started_at', db.DateTime)
    finished_by = db.Column('finished_by', db.Integer, db.ForeignKey('users.id'), default=None)
    finished_at = db.Column('finished_at', db.DateTime)
    status_changed_at = db.Column('status_changed_at', db.DateTime)
    priority_changed_at = db.Column('priority_changed_at', db.DateTime)

    orgs = db.relationship("Organisation")
    assignees = db.relationship("User", foreign_keys=[assignee])
    created_bys = db.relationship("User", foreign_keys=[created_by])
    finished_bys = db.relationship("User", foreign_keys=[finished_by])
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
        priority: int,
        created_by: int,
        created_at: datetime,
        started_at: datetime = None,
        finished_at: datetime = None,
        assignee: int = None,
        finished_by: int = None,
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
        self.started_at = started_at
        self.finished_by = finished_by
        self.finished_at = finished_at
        self.status_changed_at = status_changed_at
        self.priority_changed_at = priority_changed_at

    def as_dict(self) -> dict:
        """
        :return: dict repr of a Task object
        """
        if self.due_time is None:
            due_time = None
        else:
            due_time = self.due_time.strftime(app.config['RESPONSE_DATE_FORMAT'])

        if self.created_at is None:
            created_at = None
        else:
            created_at = self.created_at.strftime(app.config['RESPONSE_DATE_FORMAT'])

        if self.started_at is None:
            started_at = None
        else:
            started_at = self.started_at.strftime(app.config['RESPONSE_DATE_FORMAT'])

        if self.finished_at is None:
            finished_at = None
        else:
            finished_at = self.finished_at.strftime(app.config['RESPONSE_DATE_FORMAT'])

        if self.status_changed_at is None:
            status_changed_at = None
        else:
            status_changed_at = self.status_changed_at.strftime(app.config['RESPONSE_DATE_FORMAT'])

        if self.priority_changed_at is None:
            priority_changed_at = None
        else:
            priority_changed_at = self.priority_changed_at.strftime(app.config['RESPONSE_DATE_FORMAT'])

        return {
            "id": self.id,
            "org_id": self.org_id,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "time_estimate": self.time_estimate,
            "due_time": due_time,
            "assignee": self.assignee,
            "priority": self.priority,
            "created_by": self.created_by,
            "created_at": created_at,
            "started_at": started_at,
            "finished_by": self.finished_by,
            "finished_at": finished_at,
            "status_changed_at": status_changed_at,
            "priority_changed_at": priority_changed_at
        }

    def fat_dict(self) -> dict:
        """ Returns a full task dict with all of its FK's joined. """
        return _get_fat_task(self.id)

    def activity(self) -> list:
        """ Returns the activity of a task. """
        activity = task_activity_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('id').eq(self.id)
        )
        logger.info(f"Found {activity.get('Count')} activity items for user id {self.id}")

        log = []

        for item in activity.get('Items'):
            try:
                del item['id']
                log.append(item)
            except KeyError:
                logger.error(f"Key 'id' was missing from activity item. Table:{task_activity_table.name} Item:{item}")

        return log

    def label(self) -> str:
        """ Gets the label of its task type """
        from app.Controllers import TaskTypeController
        return TaskTypeController.get_task_type_by_id(self.org_id, self.type).label
