import datetime
import pytz
from os import getenv

import boto3
import structlog
from boto3.dynamodb.conditions import Key
from flask import current_app
from sqlalchemy import desc

from app.Extensions.Database import db, session_scope
from app.Extensions.Errors import ValidationError
from app.Models import Event
from app.Models.Notification import NotificationAction, Notification
from app.Models.Dao import DelayedTask, User
from app.Models.Enums import Events, Operations, Resources, TaskStatuses
from app.Models.Enums.Notifications import ClickActions, TargetTypes, NotificationIcons
from app.Models.LocalMockData import MockActivity
from app.Utilities.All import get_all_user_ids

dyn_db = boto3.resource("dynamodb")
log = structlog.getLogger()


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column("id", db.Integer, primary_key=True)
    org_id = db.Column("org_id", db.Integer, db.ForeignKey("organisations.id"))
    title = db.Column("title", db.String)
    template_id = db.Column("template_id", db.Integer, db.ForeignKey("task_templates.id"), default=None)
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
    custom_1 = db.Column("custom_1", db.String, default=None)
    custom_2 = db.Column("custom_2", db.String, default=None)
    custom_3 = db.Column("custom_3", db.String, default=None)
    display_order = db.Column("display_order", db.String)

    assigned_user = db.relationship("User", foreign_keys=[assignee], backref="assigned_user")

    def __init__(
        self,
        org_id: int,
        title: str,
        template_id: int,
        description: str,
        time_estimate: int,
        priority: int,
        created_by: int,
        display_order: int = 0,
        status: str = None,
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
        custom_1: str = None,
        custom_2: str = None,
        custom_3: str = None,
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
        self.custom_1 = custom_1
        self.custom_2 = custom_2
        self.custom_3 = custom_3
        self.display_order = display_order

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
            "labels": [_ for _ in [self.label_1, self.label_2, self.label_3] if _ is not None],
            "display_order": self.display_order,
        }

    def activity(self, max_days_of_history: int) -> list:
        """Returns the activity of a task."""
        if max_days_of_history == -1:
            # all time, THE TIME OF THIS ORIGINAL COMMIT
            start_of_history = datetime.datetime(2019, 12, 6, 22, 51, 7, 856186)
        else:
            start_of_history = datetime.datetime.utcnow() - datetime.timedelta(days=max_days_of_history)

        start_of_history_str = start_of_history.strftime(current_app.config["DYN_DB_ACTIVITY_DATE_FORMAT"])

        log.info(
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

        log.info(f"Found {activity.get('Count')} activity items for task id {self.id}")

        activity_log = []

        for item in activity.get("Items"):
            activity_timestamp = datetime.datetime.strptime(
                item["activity_timestamp"], current_app.config["DYN_DB_ACTIVITY_DATE_FORMAT"]
            )
            activity_timestamp = pytz.utc.localize(activity_timestamp)
            item["activity_timestamp"] = activity_timestamp.strftime(current_app.config["RESPONSE_DATE_FORMAT"])
            activity_log.append(item)

        return activity_log

    def delayed_info(self) -> dict:
        """Gets the latest delayed information about a task"""
        from app.Models.Dao import User

        with session_scope() as session:
            qry = (
                session.query(DelayedTask, User.first_name, User.last_name)
                .join(Task, DelayedTask.task_id == self.id)
                .join(User, DelayedTask.delayed_by == User.id)
                .order_by(desc(DelayedTask.delayed_at))
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
        """Drops this task"""
        old_assignee = self.assigned_user.name()
        self.unassign(req_user)

        self.transition(status=TaskStatuses.READY, req_user=req_user)

        dropped_notification = Notification(
            title="Task dropped",
            event_name=Events.task_transitioned_ready,
            msg=f"{self.title} has been dropped by {req_user.name()}.",
            target_type=TargetTypes.TASK,
            target_id=self.id,
            actions=[NotificationAction(ClickActions.ASSIGN_TO_ME, NotificationIcons.ASSIGN_TO_ME_ICON)],
            user_ids=get_all_user_ids(req_user.org_id, exclude=[req_user.id]),
        )
        dropped_notification.push()

        req_user.log(Operations.DROP, Resources.TASK, resource_id=self.id)
        log.info(f"User {req_user.id} dropped task {self.id} which was assigned to {old_assignee}.")

    def assign(self, assignee: int, req_user: User, notify: bool = True) -> None:
        """Common function for assigning a task"""
        # set the task assignee
        with session_scope():
            self.assignee = assignee

        # get the assigned user
        assigned_user = self.assigned_user

        # don't notify the assignee if they assigned themselves to the task
        if assigned_user.id == req_user.id:
            notify = False

        Event(
            org_id=self.org_id,
            event=Events.task_assigned,
            event_id=self.id,
            event_friendly=f"{assigned_user.name()} assigned to task by {req_user.name()}.",
        ).publish()
        Event(
            org_id=req_user.org_id,
            event=Events.user_assigned_task,
            event_id=req_user.id,
            event_friendly=f"Assigned {assigned_user.name()} to {self.title}.",
        ).publish()
        Event(
            org_id=assigned_user.org_id,
            event=Events.user_assigned_to_task,
            event_id=assigned_user.id,
            event_friendly=f"Assigned to {self.title} by {req_user.name()}.",
        ).publish()
        if notify:
            assigned_notification = Notification(
                title="You've been assigned a task!",
                event_name=Events.user_assigned_to_task,
                msg=f"{req_user.name()} assigned {self.title} to you.",
                target_id=self.id,
                target_type=TargetTypes.TASK,
                actions=[NotificationAction(ClickActions.VIEW_TASK, NotificationIcons.VIEW_TASK_ICON)],
                user_ids=[assigned_user.id],
            )
            assigned_notification.push()
        req_user.log(Operations.ASSIGN, Resources.TASK, resource_id=self.id)
        log.info(f"assigned task {self.id} to user {assignee}")

    def change_priority(self, priority: int, notification_exclusions: list = None) -> None:
        """Change the tasks priority"""
        with session_scope():
            if priority > self.priority:
                # task priority is increasing
                priority_notification = Notification(
                    title="Task escalated",
                    event_name=Events.task_escalated,
                    msg=f"{self.title} task has been escalated.",
                    target_type=TargetTypes.TASK,
                    target_id=self.id,
                    actions=[NotificationAction(ClickActions.ASSIGN_TO_ME, NotificationIcons.VIEW_TASK_ICON)],
                    user_ids=get_all_user_ids(self.org_id, exclude=notification_exclusions),
                )
                priority_notification.push()
            self.priority = priority
            self.priority_changed_at = datetime.datetime.utcnow()
        log.info(f"Changed task {self.id} priority to {priority}")

    def unassign(self, req_user: User) -> None:
        """Common function for unassigning a task"""
        # only proceed if the task is assigned to someone
        if self.assignee is not None:
            # get the old assignee
            old_assignee = self.assigned_user

            with session_scope():
                self.assignee = None

            Event(
                org_id=self.org_id,
                event=Events.task_unassigned,
                event_id=self.id,
                event_friendly=f"{old_assignee.name()} unassigned from task by {req_user.name()}.",
            ).publish()
            Event(
                org_id=req_user.org_id,
                event=Events.user_unassigned_task,
                event_id=req_user.id,
                event_friendly=f"Unassigned {old_assignee.name()} from {self.title}.",
            ).publish()
            Event(
                org_id=old_assignee.org_id,
                event=Events.user_unassigned_from_task,
                event_id=old_assignee.id,
                event_friendly=f"Unassigned from {self.title} by {req_user.name()}.",
            ).publish()
            req_user.log(Operations.ASSIGN, Resources.TASK, resource_id=self.id)
            log.info(f"Unassigned user {old_assignee.id} from task {self.id}")

    def transition(self, status: str, req_user: User = None) -> None:
        """Common function for transitioning a task"""
        with session_scope() as session:
            old_status = self.status

            # don't do anything if the statuses are the same
            if status == old_status:
                return

            # don't transition a task if it's not assigned to anyone - unless it's being cancelled
            if old_status == TaskStatuses.READY and self.assignee is None and status != TaskStatuses.CANCELLED:
                raise ValidationError("Cannot move task out of ready because it's not assigned to anyone.")

            # remove delayed task if the new status isn't DELAYED
            if old_status == TaskStatuses.DELAYED and status != TaskStatuses.DELAYED:
                delayed_task = session.query(DelayedTask).filter_by(task_id=self.id, expired=None).first()
                delayed_task.expired = datetime.datetime.utcnow()
                delayed_task.delay_for = (datetime.datetime.utcnow() - delayed_task.delayed_at).seconds

            # assign finished_by and _at if the task is being completed
            if status in (TaskStatuses.COMPLETED, TaskStatuses.CANCELLED):
                self.finished_by = req_user.id
                self.finished_at = datetime.datetime.utcnow()

            # assign started_at if the task is being started for the first time
            if status == TaskStatuses.IN_PROGRESS and self.started_at is None:
                self.started_at = datetime.datetime.utcnow()

            # update task status and status_changed_at
            self.status = status
            self.status_changed_at = datetime.datetime.utcnow()

        # get the pretty labels for the old and new status
        old_status_label = self._pretty_status_label(old_status)
        new_status_label = self._pretty_status_label(status)

        Event(
            org_id=self.org_id,
            event=f"task_transitioned_{self.status.lower()}",
            event_id=self.id,
            event_friendly=f"Transitioned from {old_status_label} to {new_status_label}.",
        ).publish()

        # req_user will be none when this is called from a service account
        if req_user is None:
            return

        Event(
            org_id=req_user.org_id,
            event=Events.user_transitioned_task,
            event_id=req_user.id,
            event_friendly=f"Transitioned {self.title} from {old_status_label} to {new_status_label}.",
        ).publish()
        req_user.log(Operations.TRANSITION, Resources.TASK, resource_id=self.id)
        log.info(f"User {req_user.id} transitioned task {self.id} from {old_status} to {status}")

    @staticmethod
    def _pretty_status_label(status: str) -> str:
        """Converts a task status from IN_PROGRESS to 'In Progress'"""
        if "_" in status:
            words = status.lower().split("_")
            return " ".join([w.capitalize() for w in words])
        else:
            return status.lower().capitalize()
