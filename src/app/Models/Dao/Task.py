import datetime
import pytz
from os import getenv

from boto3.dynamodb.conditions import Key
from flask import current_app
import boto3

from app.Extensions.Database import db, session_scope
from app.Extensions.Errors import ValidationError
from app.Models.Dao import DelayedTask, User
from app.Models.LocalMockData import MockActivity

dyn_db = boto3.resource("dynamodb")


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column("id", db.Integer, primary_key=True)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    title = db.Column("title", db.String)
    template_id = db.Column("template_id", db.Integer, db.ForeignKey("task_templates.id"))
    description = db.Column("description", db.String)
    status = db.Column("status", db.String, db.ForeignKey("task_statuses.status"))
    time_estimate = db.Column("time_estimate", db.Integer, default=0)
    scheduled_for = db.Column("scheduled_for", db.DateTime, default=None)
    scheduled_notification_period = db.Column("scheduled_notification_period", db.Integer, default=None)
    scheduled_notification_sent = db.Column("scheduled_notification_sent", db.DateTime, default=None)
    assignee = db.Column("assignee", db.Integer, db.ForeignKey("users.id"), default=None)
    priority = db.Column("priority", db.Integer, db.ForeignKey("task_priorities.priority"), default=1)
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column("created_at", db.DateTime, default=datetime.datetime.utcnow)
    started_at = db.Column("started_at", db.DateTime)
    finished_by = db.Column("finished_by", db.Integer, db.ForeignKey("users.id"), default=None)
    finished_at = db.Column("finished_at", db.DateTime)
    status_changed_at = db.Column("status_changed_at", db.DateTime)
    priority_changed_at = db.Column("priority_changed_at", db.DateTime)
    label_1 = db.Column("label_1", db.Integer, default=None)
    label_2 = db.Column("label_2", db.Integer, default=None)
    label_3 = db.Column("label_3", db.Integer, default=None)

    assignees = db.relationship("User", foreign_keys=[assignee], backref="assigned_user")

    def __init__(
        self,
        org_id: int,
        title: str,
        template_id: int,
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
        label_3: int = None,
    ):
        self.org_id = org_id
        self.title = title
        self.template_id = template_id
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
            created_at = pytz.utc.localize(self.created_at)
            created_at = created_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.started_at is None:
            started_at = None
        else:
            started_at = pytz.utc.localize(self.started_at)
            started_at = started_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.finished_at is None:
            finished_at = None
        else:
            finished_at = pytz.utc.localize(self.finished_at)
            finished_at = finished_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.status_changed_at is None:
            status_changed_at = None
        else:
            status_changed_at = pytz.utc.localize(self.status_changed_at)
            status_changed_at = status_changed_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.priority_changed_at is None:
            priority_changed_at = None
        else:
            priority_changed_at = pytz.utc.localize(self.priority_changed_at)
            priority_changed_at = priority_changed_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.scheduled_for is None:
            scheduled_for = None
        else:
            scheduled_for = pytz.utc.localize(self.scheduled_for)
            scheduled_for = scheduled_for.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        if self.scheduled_notification_sent is None:
            scheduled_notification_sent = None
        else:
            scheduled_notification_sent = pytz.utc.localize(self.scheduled_notification_sent)
            scheduled_notification_sent = scheduled_notification_sent.strftime(
                current_app.config["RESPONSE_DATE_FORMAT"]
            )

        return {
            "id": self.id,
            "org_id": self.org_id,
            "template_id": self.template_id,
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
            "labels": [l for l in [self.label_1, self.label_2, self.label_3] if l is not None],
        }

    def activity(self, max_days_of_history: int) -> list:
        """ Returns the activity of a task. """
        if max_days_of_history == -1:
            # all time, THE TIME OF THIS ORIGINAL COMMIT
            start_of_history = datetime.datetime(2019, 12, 6, 22, 51, 7, 856186)
        else:
            start_of_history = datetime.datetime.utcnow() - datetime.timedelta(days=max_days_of_history)

        start_of_history_str = start_of_history.strftime(current_app.config["DYN_DB_ACTIVITY_DATE_FORMAT"])

        current_app.logger.info(
            f"Retrieving {max_days_of_history} days of history "
            f"({start_of_history.strftime('%Y-%m-%d %H:%M:%S')} "
            f"to {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}) for task {self.id}. "
        )

        if getenv("MOCK_AWS"):
            activity = MockActivity()
            return activity.data

        task_activity_table = dyn_db.Table(current_app.config["TASK_ACTIVITY_TABLE"])

        activity = task_activity_table.query(
            Select="ALL_ATTRIBUTES",
            KeyConditionExpression=Key("id").eq(self.id) & Key("activity_timestamp").gte(start_of_history_str),
            ScanIndexForward=False,
        )

        current_app.logger.info(f"Found {activity.get('Count')} activity items for task id {self.id}")

        log = []

        for item in activity.get("Items"):
            activity_timestamp = datetime.datetime.strptime(
                item["activity_timestamp"], current_app.config["DYN_DB_ACTIVITY_DATE_FORMAT"]
            )
            activity_timestamp = pytz.utc.localize(activity_timestamp)
            item["activity_timestamp"] = activity_timestamp.strftime(current_app.config["RESPONSE_DATE_FORMAT"])
            log.append(item)

        return log

    def delayed_info(self) -> dict:
        """ Gets the latest delayed information about a task """
        from app.Models.Dao import User

        with session_scope() as session:
            qry = (
                session.query(DelayedTask, User.first_name, User.last_name)
                .join(User, DelayedTask.delayed_by == User.id)
                .filter(Task.id == self.id)
                .first()
            )

        if qry is None:
            raise ValidationError("Task has not been delayed before.")
        else:
            task, db_fn, db_ln = qry
            delayed_task_dict = task.as_dict()
            delayed_task_dict["delayed_by"] = db_fn + " " + db_ln
            return delayed_task_dict

    def drop(self, req_user: User) -> None:
        """ Drops this task """
        from app.Services import TaskService

        TaskService().drop(self, req_user)
