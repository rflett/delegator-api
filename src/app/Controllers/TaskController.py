import datetime
import typing
from dateutil import tz

from flask import request, Response
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from app import logger, session_scope, subscription_api
from app.Exceptions import ValidationError
from app.Controllers import NotificationController
from app.Controllers.Base import RequestValidationController
from app.Models import User, Task, DelayedTask, Activity, TaskPriority, TaskStatus
from app.Models.Enums import TaskStatuses, Events, Operations, Resources


class TaskController(RequestValidationController):
    @staticmethod
    def _pretty_status_label(status: str) -> str:
        """Converts a task status from IN_PROGRESS to 'In Progress' """
        if "_" in status:
            words = status.lower().split('_')
            return " ".join([w.capitalize() for w in words])
        else:
            return status.lower().capitalize()

    def _transition_task(self, task: Task, status: str, req_user: User) -> None:
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

        # get the pretty labels for the old and new status
        old_status_label = self._pretty_status_label(old_status)
        new_status_label = self._pretty_status_label(status)

        Activity(
            org_id=task.org_id,
            event=f'task_transitioned_{task.status.lower()}',
            event_id=task.id,
            event_friendly=f"Transitioned from {old_status_label} to {new_status_label}."
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_transitioned_task,
            event_id=req_user.id,
            event_friendly=f"Transitioned {task.label()} from {old_status_label} to {new_status_label}."
        ).publish()
        req_user.log(
            operation=Operations.TRANSITION,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"User {req_user.id} transitioned task {task.id} from {old_status} to {status}")

    @staticmethod
    def _assign_task(task: Task, assignee: int, req_user: User) -> None:
        """Common function for assigning a task """
        from app.Controllers import UserController

        # set the task assignee
        with session_scope():
            task.assignee = assignee

        # get the assigned user
        assigned_user = UserController.get_user_by_id(assignee)
        Activity(
            org_id=task.org_id,
            event=Events.task_assigned,
            event_id=task.id,
            event_friendly=f"{assigned_user.name()} assigned to task by {req_user.name()}."
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_assigned_task,
            event_id=req_user.id,
            event_friendly=f"Assigned {assigned_user.name()} to {task.label()}."
        ).publish()
        Activity(
            org_id=assigned_user.org_id,
            event=Events.user_assigned_to_task,
            event_id=assigned_user.id,
            event_friendly=f"Assigned to {task.label()} by {req_user.name()}."
        ).publish()
        NotificationController().push(
            msg="You've been assigned a task!",
            user_ids=assigned_user.id
        )
        req_user.log(
            operation=Operations.ASSIGN,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"assigned task {task.id} to user {assignee}")

    @staticmethod
    def _unassign_task(task: Task, req_user: User) -> None:
        """Common function for unassigning a task """
        from app.Controllers import UserController

        # only proceed if the task is assigned to someone
        if task.assignee is not None:
            # get the old assignee
            old_assignee = UserController.get_user_by_id(task.assignee)

            with session_scope():
                task.assignee = None

            Activity(
                org_id=task.org_id,
                event=Events.task_unassigned,
                event_id=task.id,
                event_friendly=f"{old_assignee.name()} unassigned from task by {req_user.name()}."
            ).publish()
            Activity(
                org_id=req_user.org_id,
                event=Events.user_unassigned_task,
                event_id=req_user.id,
                event_friendly=f"Unassigned {old_assignee.name()} from {task.label()}."
            ).publish()
            Activity(
                org_id=old_assignee.org_id,
                event=Events.user_unassigned_from_task,
                event_id=old_assignee.id,
                event_friendly=f"Unassigned from {task.label()} by {req_user.name()}."
            ).publish()
            req_user.log(
                operation=Operations.ASSIGN,
                resource=Resources.TASK,
                resource_id=task.id
            )
            logger.info(f"Unassigned user {old_assignee.id} from task {task.id}")

    def _change_task_priority(self, task: Task, priority: int) -> None:
        """Common function for changing a tasks priority"""
        with session_scope():
            if priority > task.priority:
                task.priority = priority
                task.priority_changed_at = datetime.datetime.utcnow()
                # task priority is increasing
                NotificationController().push(
                    msg=f"{task.label()} task has been escalated.",
                    user_ids=self._all_user_ids(task.org_id)
                )

        logger.info(f"Changed task {task.id} priority to {priority}")

    def _drop(self, task: Task, req_user: User) -> None:
        """Drops a task"""
        self._unassign_task(task, req_user)

        self._transition_task(
            task=task,
            status=TaskStatuses.READY,
            req_user=req_user
        )

        NotificationController().push(
            msg=f"{task.label()} has been dropped.",
            user_ids=self._all_user_ids(req_user.org_id)
        )

        req_user.log(
            operation=Operations.DROP,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"User {req_user.id} dropped task {task.id} "
                    f"which was assigned to {task.assignee}.")

    @staticmethod
    def _get_task(task_id: int, org_id: int) -> Task:
        """Gets a task by its ID, raises a ValidationError if it doesn't exist"""
        with session_scope() as session:
            task = session.query(Task).filter_by(id=task_id, org_id=org_id).first()
            if task is None:
                raise ValidationError("Task does not exist")
            else:
                return task

    @staticmethod
    def _all_user_ids(org_id: int) -> typing.List[int]:
        """ Returns a list of all user ids """
        with session_scope() as session:
            user_ids_qry = session.query(User.id).filter_by(org_id=org_id).all()

        return [user_id[0] for user_id in user_ids_qry]

    def get_task_priorities(self, **kwargs) -> Response:
        """Returns all task priorities """
        req_user = kwargs['req_user']

        with session_scope() as session:
            task_pr_qry = session.query(TaskPriority).all()

        task_priorities = [tp.as_dict() for tp in task_pr_qry]
        logger.debug(f"Found {len(task_priorities)} task_priorities.")
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_PRIORITIES
        )
        return self.ok(task_priorities)

    def get_task_statuses(self, **kwargs) -> Response:
        """Returns all task statuses """
        req_user = kwargs['req_user']

        with session_scope() as session:
            task_status_qry = session.query(TaskStatus).all()

        task_statuses = [ts.as_dict() for ts in task_status_qry if ts.status not in ["DELAYED", "CANCELLED"]]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_STATUSES
        )
        return self.ok(task_statuses)

    def get_task(self, task_id: int, **kwargs) -> Response:
        """Get a single task by its id """
        req_user = kwargs['req_user']

        task = self._get_task(task_id, req_user.org_id)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK,
            resource_id=task.id
        )
        return self.ok(task.fat_dict())

    def get_tasks(self, **kwargs) -> Response:
        """Get all tasks in an organisation """
        req_user = kwargs['req_user']

        # start_period, end_period = self.validate_time_period(req.get_json())
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        # join across all related tables to get full info
        with session_scope() as session:
            task_assignee, task_created_by, task_finished_by = aliased(User), aliased(User), aliased(User)
            tasks_qry = session\
                .query(Task, task_assignee, task_created_by, task_finished_by) \
                .outerjoin(task_assignee, task_assignee.id == Task.assignee) \
                .outerjoin(task_finished_by, task_finished_by.id == Task.finished_by) \
                .join(task_created_by, task_created_by.id == Task.created_by) \
                .join(Task.created_bys) \
                .filter(
                    and_(
                        Task.org_id == req_user.org_id,
                        or_(
                            and_(
                                Task.finished_at >= start_period,
                                Task.finished_at <= end_period
                            ),
                            Task.finished_at == None  # noqa
                        )
                    )
                ).all()

        tasks = []

        for t, ta, tcb, tfb in tasks_qry:
            task_dict = t.as_dict()
            task_dict['assignee'] = ta.as_dict() if ta is not None else None
            task_dict['created_by'] = tcb.as_dict()
            task_dict['finished_by'] = tfb.as_dict() if tfb is not None else None
            task_dict['status'] = t.task_statuses.as_dict()
            task_dict['type'] = t.task_types.as_dict()
            task_dict['priority'] = t.task_priorities.as_dict()
            tasks.append(task_dict)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASKS
        )
        return self.ok(tasks)

    def create_task(self, **kwargs) -> Response:
        """Creates a task"""
        req_user = kwargs['req_user']

        task_attrs = self.validate_create_task_request(request.get_json(), **kwargs)

        # create task
        with session_scope() as session:
            task = Task(
                org_id=req_user.org_id,
                type=task_attrs.get('type'),
                description=task_attrs.get('description'),
                status=task_attrs.get('status'),
                time_estimate=task_attrs.get('time_estimate'),
                due_time=task_attrs.get('due_time'),
                priority=task_attrs.get('priority'),
                created_by=req_user.id,
                created_at=task_attrs.get('created_at'),
                finished_at=task_attrs.get('finished_at')
            )
            session.add(task)

        Activity(
            org_id=task.org_id,
            event=Events.task_created,
            event_id=task.id,
            event_friendly=f"Created by {req_user.name()}."
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_created_task,
            event_id=req_user.id,
            event_friendly=f"Created task {task.label()}."
        ).publish()
        req_user.log(
            operation=Operations.CREATE,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"created task {task.as_dict()}")

        # optionally assign the task if an assignee was present in the create task request
        if task_attrs.get('assignee') is not None:
            self._assign_task(
                task=task,
                assignee=task_attrs.get('assignee'),
                req_user=req_user
            )
        else:
            NotificationController().push(
                msg=f"{task.label()} task has been created.",
                user_ids=self._all_user_ids(req_user.org_id)
            )

        return self.created(task.fat_dict())

    def update_task(self, **kwargs) -> Response:
        """Update a task """
        req_user = kwargs['req_user']

        task_attrs = self.validate_update_task_request(request.get_json(), **kwargs)

        # update the task
        task_to_update = task_attrs['task']

        # if the assignee isn't the same as before then assign someone to it, if the new assignee is null or
        # omitted from the request, then assign the task
        assignee = task_attrs.pop('assignee', None)
        if task_to_update.assignee != assignee:
            if assignee is None:
                self._unassign_task(
                    task=task_to_update,
                    req_user=req_user
                )
            else:
                self._assign_task(
                    task=task_to_update,
                    assignee=assignee,
                    req_user=req_user
                )

        # transition
        task_status = task_attrs.pop('status')
        if task_to_update.status != task_status:
            self._transition_task(
                task=task_to_update,
                status=task_status,
                req_user=req_user
            )

        # change priority
        task_priority = task_attrs.pop('priority')
        if task_to_update.priority != task_priority:
            self._change_task_priority(
                task=task_to_update,
                priority=task_priority
            )

        # for each value in the request body, if the task has that attribute, update it
        # previous attributes such as priority and status have been popped from the request dict so will not be updated
        # again here
        with session_scope():
            for k, v in task_attrs.items():
                task_to_update.__setattr__(k, v)

        # publish event
        Activity(
            org_id=task_to_update.org_id,
            event=Events.task_updated,
            event_id=task_to_update.id,
            event_friendly=f"Updated by {req_user.name()}."
        ).publish()
        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.TASK,
            resource_id=task_to_update.id
        )
        return self.ok(task_to_update.fat_dict())

    def assign_task(self, **kwargs) -> Response:
        """Assigns a user to task """
        task, assignee_id = self.validate_assign_task(request.get_json(), **kwargs)
        self._assign_task(
            task=task,
            assignee=assignee_id,
            req_user=kwargs['req_user']
        )
        return self.ok(task.fat_dict())

    def drop_task(self, task_id, **kwargs) -> Response:
        """
        Drops a task, which sets it to READY and removes the assignee
        if the task is IN_PROGRESS and has an assignee
        """
        task_to_drop = self.validate_drop_task(task_id, **kwargs)
        self._drop(task_to_drop, kwargs['req_user'])
        return self.ok(task_to_drop.fat_dict())

    def cancel_task(self, task_id, **kwargs) -> Response:
        """Cancels a task """
        req_user = kwargs['req_user']

        task_to_cancel = self.validate_cancel_task(task_id, **kwargs)

        self._transition_task(
            task=task_to_cancel,
            status=TaskStatuses.CANCELLED,
            req_user=req_user
        )
        req_user.log(
            operation=Operations.CANCEL,
            resource=Resources.TASK,
            resource_id=task_id
        )
        if task_to_cancel.assignee is not None:
            NotificationController().push(
                msg=f"{task_to_cancel.label()} cancelled.",
                user_ids=task_to_cancel.assignee
            )
        logger.info(f"User {req_user.id} cancelled task {task_to_cancel.id}")
        return self.ok(task_to_cancel.fat_dict())

    def transition_task(self, **kwargs) -> Response:
        """Transitions the status of a task """
        task, task_status = self.validate_transition_task(request.get_json(), **kwargs)

        self._transition_task(
            task=task,
            status=task_status,
            req_user=kwargs['req_user']

        )
        return self.ok(task.fat_dict())

    def get_available_transitions(self, task_id: int, **kwargs) -> Response:
        """Returns the statuses that a task could be transitioned to, based on the state of the task. """
        req_user = kwargs['req_user']

        task = self.validate_get_transitions(req_user.org_id, task_id)

        ret = []

        # handle case where no-one is assigned to the task
        if task.assignee is None:
            # you can move from ready to ready, cancelled and dropped are not included because they are handled
            # separately
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY]
            }

            # search list for querying db
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                # will return all the attributes for the ready status
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                # will return all other statuses
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # enabled options
            ret += [ts.as_dict() for ts in enabled_qry]

            # disabled options
            ret += [ts.as_dict(disabled=True, tooltip="No one is assigned to this task.") for ts in disabled_qry]

        else:
            # if someone is assigned to the task, then these are the available transitions
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY, TaskStatuses.IN_PROGRESS, TaskStatuses.CANCELLED],
                TaskStatuses.IN_PROGRESS: [TaskStatuses.IN_PROGRESS, TaskStatuses.COMPLETED],
                TaskStatuses.DELAYED: [TaskStatuses.DELAYED, TaskStatuses.IN_PROGRESS]
            }

            # search list for querying db
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                # will return all attributes for the enabled tasks
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                # will return attributes for all other tasks
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # enabled options
            ret += [ts.as_dict() for ts in enabled_qry if ts.status not in ["DELAYED", "CANCELLED"]]

            # disabled options
            ret += [ts.as_dict(disabled=True) for ts in disabled_qry if ts.status not in ["DELAYED", "CANCELLED"]]

        return self.ok(ret)

    @staticmethod
    def delay_task(self, **kwargs) -> Response:
        """Delays a task """
        req_user = kwargs['req_user']

        task, delay_for, reason = self.validate_delay_task_request(request.get_json(), **kwargs)

        with session_scope() as session:
            # transition a task to delayed
            self._transition_task(
                task=task,
                status=TaskStatuses.DELAYED,
                req_user=req_user
            )
            # check to see if the task has been delayed previously
            delay = session.query(DelayedTask).filter_by(task_id=task.id).first()

            # if the task has been delayed before, update it, otherwise create it
            if delay is not None:
                delay.delay_for = delay_for
                delay.delayed_at = datetime.datetime.utcnow()
                delay.snoozed = None
                if reason is not None:
                    delay.reason = reason
            else:
                delayed_task = DelayedTask(
                    task_id=task.id,
                    delay_for=delay_for,
                    delayed_at=datetime.datetime.utcnow(),
                    delayed_by=req_user.id,
                    reason=reason
                )
                session.add(delayed_task)

        if req_user.id == task.assignee:
            NotificationController().push(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.created_by
            )
        elif req_user.id == task.created_by:
            NotificationController().push(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.assignee
            )

        req_user.log(
            operation=Operations.DELAY,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"User {req_user.id} delayed task {task.id} for {delay_for}s.")
        return self.ok(task.fat_dict())

    def get_delayed_task(self, task_id: int, **kwargs) -> Response:
        """Returns the delayed info for a task """
        req_user = kwargs['req_user']

        task = self._get_task(task_id, req_user.org_id)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK,
            resource_id=task.id
        )

        return self.ok(task.delayed_info())

    def get_task_activity(self, task_id: int, **kwargs) -> Response:
        """Returns the activity for a task """
        req_user = kwargs['req_user']

        plan_limits = subscription_api.get_limits(req_user.orgs.chargebee_subscription_id)
        activity_log_history_limit = plan_limits.get('task_activity_log_history', 7)

        # get the task
        task = self._get_task(task_id, req_user.org_id)
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_ACTIVITY,
            resource_id=task.id
        )
        logger.info(f"Getting activity for task with id {task.id}")
        return self.ok(task.activity(activity_log_history_limit))

    def change_priority(self) -> Response:
        """ Change a tasks priority """
        request_body = request.get_json()
        params = {
            "org_id": request_body.get('org_id'),
            "task_id": request_body.get('task_id'),
            "priority": request_body.get('priority'),
        }
        for k, v in params.items():
            if v is None:
                raise ValidationError(f"Missing {k} from request")

        task = self._get_task(params['task_id'], params['org_id'])
        self._change_task_priority(
            task=task,
            priority=params['priority']
        )
        return self.ok(f"Priority changed for task {params['task_id']}")
