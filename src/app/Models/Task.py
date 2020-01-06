import datetime
from os import getenv

from boto3.dynamodb.conditions import Key
from sqlalchemy.orm import aliased

from app import db, session_scope, logger, task_activity_table, app, app_env
from app.Exceptions import ValidationError
from app.Models import DelayedTask, User
from app.Models.LocalMockData import MockActivity


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column('id', db.Integer, primary_key=True)
    org_id = db.Column('org_id', db.Integer, db.ForeignKey('organisations.id'))
    type = db.Column('type', db.Integer, db.ForeignKey('task_types.id'))
    description = db.Column('description', db.String)
    status = db.Column('status', db.String, db.ForeignKey('task_statuses.status'))
    time_estimate = db.Column('time_estimate', db.Integer, default=0)
    scheduled_for = db.Column('scheduled_for', db.DateTime, default=None)
    scheduled_notification_period = db.Column('scheduled_notification_period', db.Integer, default=None)
    scheduled_notification_sent = db.Column('scheduled_notification_sent', db.DateTime, default=None)
    assignee = db.Column('assignee', db.Integer, db.ForeignKey('users.id'), default=None)
    priority = db.Column('priority', db.Integer, db.ForeignKey('task_priorities.priority'), default=1)
    created_by = db.Column('created_by', db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)
    started_at = db.Column('started_at', db.DateTime)
    finished_by = db.Column('finished_by', db.Integer, db.ForeignKey('users.id'), default=None)
    finished_at = db.Column('finished_at', db.DateTime)
    status_changed_at = db.Column('status_changed_at', db.DateTime)
    priority_changed_at = db.Column('priority_changed_at', db.DateTime)
    label_1 = db.Column('label_1', db.Integer, default=None)
    label_2 = db.Column('label_2', db.Integer, default=None)
    label_3 = db.Column('label_3', db.Integer, default=None)

    orgs = db.relationship("Organisation", backref="organisations")
    assignees = db.relationship("User", foreign_keys=[assignee], backref="assigned_user")
    created_bys = db.relationship("User", foreign_keys=[created_by], backref="created_by_user")
    finished_bys = db.relationship("User", foreign_keys=[finished_by], backref="finished_by_user")
    task_statuses = db.relationship("TaskStatus", backref="task_statuses")
    task_types = db.relationship("TaskType", backref="task_types")
    task_priorities = db.relationship("TaskPriority", backref="task_priorities")

    def __init__(
        self,
        org_id: int,
        type: int,
        description: str,
        status: str,
        time_estimate: int,
        priority: int,
        created_by: int,
        created_at: datetime = None,
        scheduled_for: datetime = None,
        scheduled_notification_period: int = None,
        scheduled_notification_sent: datetime = None,
        started_at: datetime = None,
        finished_at: datetime = None,
        assignee: int = None,
        finished_by: int = None,
        status_changed_at: datetime = None,
        priority_changed_at: datetime = None,
        label_1: int = None,
        label_2: int = None,
        label_3: int = None
    ):
        self.org_id = org_id
        self.type = type
        self.description = description
        self.status = status
        self.time_estimate = time_estimate
        self.scheduled_for = scheduled_for
        self.scheduled_notification_period = scheduled_notification_period
        self.scheduled_notification_sent = scheduled_notification_sent
        self.assignee = assignee
        self.priority = priority
        self.created_by = created_by
        self.created_at = created_at
        self.started_at = started_at
        self.finished_by = finished_by
        self.finished_at = finished_at
        self.status_changed_at = status_changed_at
        self.priority_changed_at = priority_changed_at
        self.label_1 = label_1
        self.label_2 = label_2
        self.label_3 = label_3

    def as_dict(self) -> dict:
        """
        :return: dict repr of a Task object
        """
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

        if self.scheduled_for is None:
            scheduled_for = None
        else:
            scheduled_for = self.scheduled_for.strftime(app.config['RESPONSE_DATE_FORMAT'])

        if self.scheduled_notification_sent is None:
            scheduled_notification_sent = None
        else:
            scheduled_notification_sent = self.scheduled_notification_sent.strftime(app.config['RESPONSE_DATE_FORMAT'])

        return {
            "id": self.id,
            "org_id": self.org_id,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "time_estimate": self.time_estimate,
            "scheduled_for": scheduled_for,
            "scheduled_notification_period": self.scheduled_notification_period,
            "scheduled_notification_sent": scheduled_notification_sent,
            "assignee": self.assignee,
            "priority": self.priority,
            "created_by": self.created_by,
            "created_at": created_at,
            "started_at": started_at,
            "finished_by": self.finished_by,
            "finished_at": finished_at,
            "status_changed_at": status_changed_at,
            "priority_changed_at": priority_changed_at,
            "labels": [l for l in [self.label_1, self.label_2, self.label_3] if l is not None]
        }

    def fat_dict(self) -> dict:
        """ Returns a full task dict with all of its FK's joined. """
        from app.Models import User, TaskLabel
        with session_scope() as session:
            task_assignee, task_created_by, task_finished_by = aliased(User), aliased(User), aliased(User)
            task_label_1, task_label_2, task_label_3 = aliased(TaskLabel), aliased(TaskLabel), aliased(TaskLabel)
            tasks_qry = session\
                .query(
                    Task,
                    task_assignee,
                    task_created_by,
                    task_finished_by,
                    task_label_1,
                    task_label_2,
                    task_label_3
                ) \
                .outerjoin(task_assignee, task_assignee.id == Task.assignee) \
                .outerjoin(task_finished_by, task_finished_by.id == Task.finished_by) \
                .outerjoin(task_label_1, task_label_1.id == Task.label_1) \
                .outerjoin(task_label_2, task_label_2.id == Task.label_2) \
                .outerjoin(task_label_3, task_label_3.id == Task.label_3) \
                .join(task_created_by, task_created_by.id == Task.created_by) \
                .filter(Task.id == self.id) \
                .first()

        t, ta, tcb, tfb, tla, tlb, tlc = tasks_qry

        task_dict = self.as_dict()

        task_dict['assignee'] = ta.as_dict() if ta is not None else None
        task_dict['created_by'] = tcb.as_dict()
        task_dict['finished_by'] = tfb.as_dict() if tfb is not None else None
        task_dict['status'] = self.task_statuses.as_dict()
        task_dict['type'] = self.task_types.as_dict()
        task_dict['priority'] = self.task_priorities.as_dict()
        task_dict['labels'] = [l.as_dict() for l in [tla, tlb, tlc] if l is not None]

        return task_dict

    def activity(self, max_days_of_history: int) -> list:
        """ Returns the activity of a task. """
        if max_days_of_history == -1:
            # all time, THE TIME OF THIS ORIGINAL COMMIT
            start_of_history = datetime.datetime(2019, 12, 6, 22, 51, 7, 856186)
        else:
            start_of_history = datetime.datetime.utcnow() - datetime.timedelta(days=max_days_of_history)

        start_of_history_str = start_of_history.strftime(app.config['DYN_DB_ACTIVITY_DATE_FORMAT'])

        logger.info(f"Retrieving {max_days_of_history} days of history "
                    f"({start_of_history.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"to {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}) for task {self.id}. ")

        if getenv('MOCK_AWS'):
            activity = MockActivity()
            return activity.data

        activity = task_activity_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('id').eq(self.id) & Key('activity_timestamp').gte(start_of_history_str),
            ScanIndexForward=False
        )

        logger.info(f"Found {activity.get('Count')} activity items for task id {self.id}")

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
        return self.task_types.label

    def delayed_info(self) -> dict:
        """ Gets the latest delayed information about a task """
        with session_scope() as session:
            delayed_task = session.query(DelayedTask).filter_by(task_id=self.id).first()

        if delayed_task is None:
            raise ValidationError("Task has not been delayed before.")
        else:
            delayed_task_dict = delayed_task.as_dict()
            delayed_task_dict['delayed_by'] = delayed_task.users.as_dict()
            return delayed_task_dict

    def drop(self, req_user: User) -> None:
        """ Drops this task """
        from app.Services import TaskService
        TaskService().drop(self, req_user)
