import datetime

from flask import current_app

from app.Extensions.Database import session_scope
from app.Models import Activity, Notification, NotificationAction
from app.Models.Dao import Task, User, DelayedTask
from app.Models.Enums import Events, Operations, Resources, TaskStatuses
from app.Models.Enums.Notifications import ClickActions, TargetTypes
from app.Extensions.Errors import ResourceNotFoundError, ValidationError


class TaskService(object):
    @staticmethod
    def assign(task: Task, assignee: int, req_user: User, notify: bool = True) -> None:
        """Common function for assigning a task """
        from app.Services import UserService

        # set the task assignee
        with session_scope():
            task.assignee = assignee

        # get the assigned user
        assigned_user = UserService.get_by_id(assignee)

        # don't notify the assignee if they assigned themselves to the task
        if assigned_user.id == req_user.id:
            notify = False

        Activity(
            org_id=task.org_id,
            event=Events.task_assigned,
            event_id=task.id,
            event_friendly=f"{assigned_user.name()} assigned to task by {req_user.name()}.",
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_assigned_task,
            event_id=req_user.id,
            event_friendly=f"Assigned {assigned_user.name()} to {task.title}.",
        ).publish()
        Activity(
            org_id=assigned_user.org_id,
            event=Events.user_assigned_to_task,
            event_id=assigned_user.id,
            event_friendly=f"Assigned to {task.title} by {req_user.name()}.",
        ).publish()
        if notify:
            assigned_notification = Notification(
                title="You've been assigned a task!",
                event_name=Events.user_assigned_to_task,
                msg=f"{req_user.name()} assigned {task.title} to you.",
                actions=[NotificationAction(ClickActions.VIEW_TASK, task.id, TargetTypes.TASK)],
                user_ids=[assigned_user.id]
            )
            assigned_notification.push()
        req_user.log(Operations.ASSIGN, Resources.TASK, resource_id=task.id)
        current_app.logger.info(f"assigned task {task.id} to user {assignee}")

    @staticmethod
    def change_priority(task: Task, priority: int) -> None:
        """Common function for changing a tasks priority"""
        from app.Services import UserService

        with session_scope():
            if priority > task.priority:
                task.priority = priority
                task.priority_changed_at = datetime.datetime.utcnow()
                # task priority is increasing
                priority_notification = Notification(
                    title="Task escalated",
                    event_name=Events.task_escalated,
                    msg=f"{task.title} task has been escalated.",
                    actions=[NotificationAction(ClickActions.ASSIGN_TO_ME, task.id, TargetTypes.TASK)],
                    user_ids=UserService.get_all_user_ids(task.org_id),
                )
                priority_notification.push()

        current_app.logger.info(f"Changed task {task.id} priority to {priority}")

    def drop(self, task: Task, req_user: User) -> None:
        from app.Services import UserService

        """Drops a task"""
        old_assignee = task.assignees.name()
        self.unassign(task, req_user)

        self.transition(task=task, status=TaskStatuses.READY, req_user=req_user)

        dropped_notification = Notification(
            title="Task dropped",
            event_name=Events.task_transitioned_ready,
            msg=f"{task.title} has been dropped by {req_user.name()}.",
            actions=[NotificationAction(ClickActions.ASSIGN_TO_ME, task.id, TargetTypes.TASK)],
            user_ids=UserService.get_all_user_ids(req_user.org_id),
        )
        dropped_notification.push()

        req_user.log(Operations.DROP, Resources.TASK, resource_id=task.id)
        current_app.logger.info(f"User {req_user.id} dropped task {task.id} which was assigned to {old_assignee}.")

    @staticmethod
    def get(task_id: int, org_id: int) -> Task:
        """Gets a task by its ID, raises a ResourceNotFoundError if it doesn't exist"""
        with session_scope() as session:
            task = session.query(Task).filter_by(id=task_id, org_id=org_id).first()
            if task is None:
                raise ResourceNotFoundError("Task does not exist")
            else:
                return task

    def transition(self, task: Task, status: str, req_user: User = None) -> None:
        """Common function for transitioning a task """
        with session_scope() as session:
            old_status = task.status

            # don't do anything if the statuses are the same
            if status == old_status:
                return

            # don't transition a task if it's not assigned to anyone - unless it's being cancelled
            if old_status == TaskStatuses.READY and task.assignee is None and status != TaskStatuses.CANCELLED:
                raise ValidationError("Cannot move task out of ready because it's not assigned to anyone.")

            # remove delayed task if the new status isn't DELAYED
            if old_status == TaskStatuses.DELAYED and status != TaskStatuses.DELAYED:
                delayed_task = session.query(DelayedTask).filter_by(task_id=task.id).first()
                delayed_task.expired = datetime.datetime.utcnow()

            # assign finished_by and _at if the task is being completed
            if status == TaskStatuses.COMPLETED:
                task.finished_by = req_user.id
                task.finished_at = datetime.datetime.utcnow()

            # assign started_at if the task is being started for the first time
            if status == TaskStatuses.IN_PROGRESS and task.started_at is None:
                task.started_at = datetime.datetime.utcnow()

            # update task status and status_changed_at
            task.status = status
            task.status_changed_at = datetime.datetime.utcnow()

            # reindex the display orders
            self.reindex_display_orders(task.org_id, new_position=0)
            task.display_order = 0

        # get the pretty labels for the old and new status
        old_status_label = self._pretty_status_label(old_status)
        new_status_label = self._pretty_status_label(status)

        # req_user will be none when this is called from a service account
        if req_user is None:
            return

        Activity(
            org_id=task.org_id,
            event=f"task_transitioned_{task.status.lower()}",
            event_id=task.id,
            event_friendly=f"Transitioned from {old_status_label} to {new_status_label}.",
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_transitioned_task,
            event_id=req_user.id,
            event_friendly=f"Transitioned {task.title} from {old_status_label} to {new_status_label}.",
        ).publish()
        req_user.log(Operations.TRANSITION, Resources.TASK, resource_id=task.id)
        current_app.logger.info(f"User {req_user.id} transitioned task {task.id} from {old_status} to {status}")

    @staticmethod
    def unassign(task: Task, req_user: User) -> None:
        """Common function for unassigning a task """
        from app.Services import UserService

        # only proceed if the task is assigned to someone
        if task.assignee is not None:
            # get the old assignee
            old_assignee = UserService.get_by_id(task.assignee)

            with session_scope():
                task.assignee = None

            Activity(
                org_id=task.org_id,
                event=Events.task_unassigned,
                event_id=task.id,
                event_friendly=f"{old_assignee.name()} unassigned from task by {req_user.name()}.",
            ).publish()
            Activity(
                org_id=req_user.org_id,
                event=Events.user_unassigned_task,
                event_id=req_user.id,
                event_friendly=f"Unassigned {old_assignee.name()} from {task.title}.",
            ).publish()
            Activity(
                org_id=old_assignee.org_id,
                event=Events.user_unassigned_from_task,
                event_id=old_assignee.id,
                event_friendly=f"Unassigned from {task.title} by {req_user.name()}.",
            ).publish()
            req_user.log(Operations.ASSIGN, Resources.TASK, resource_id=task.id)
            current_app.logger.info(f"Unassigned user {old_assignee.id} from task {task.id}")

    @staticmethod
    def reindex_display_orders(org_id: int, new_position: int = None):
        """Reindex the task display orders, if new_position is provided it will only re-index from that position"""
        with session_scope() as session:
            if new_position is None:
                session.execute(
                    """
                       UPDATE tasks
                       SET display_order = display_order + 1
                       WHERE org_id = :org_id
                    """,
                    {"org_id": org_id}
                )
            else:
                session.execute(
                    """
                       UPDATE tasks
                       SET display_order = display_order + 1
                       WHERE org_id = :org_id
                       AND display_order >= :new_position
                    """,
                    {"org_id": org_id, "new_position": new_position}
                )

    @staticmethod
    def _pretty_status_label(status: str) -> str:
        """Converts a task status from IN_PROGRESS to 'In Progress' """
        if "_" in status:
            words = status.lower().split("_")
            return " ".join([w.capitalize() for w in words])
        else:
            return status.lower().capitalize()
