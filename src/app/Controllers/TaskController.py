import datetime
from dateutil import tz

from flask import request, Response
from sqlalchemy import exists, and_, or_
from sqlalchemy.orm import aliased

from app import logger, session_scope, g_response, j_response, subscription_api
from app.Exceptions import ValidationError
from app.Controllers import AuthorizationController, NotificationController
from app.Models import User, Task, TaskStatus, TaskPriority, DelayedTask, Activity
from app.Models.Enums import TaskStatuses, Events, Operations, Resources


def _pretty_status_label(status: str) -> str:
    """Converts a task status from IN_PROGRESS to 'In Progress' """
    if "_" in status:
        words = status.lower().split('_')
        return " ".join([w.capitalize() for w in words])
    else:
        return status.lower().capitalize()


def _transition_task(task: Task, status: str, req_user: User) -> None:
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
    old_status_label = _pretty_status_label(old_status)
    new_status_label = _pretty_status_label(status)

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
    NotificationController.push(
        msg="You've been assigned a task!",
        user_ids=assigned_user.id
    )
    req_user.log(
        operation=Operations.ASSIGN,
        resource=Resources.TASK,
        resource_id=task.id
    )
    logger.info(f"assigned task {task.id} to user {assignee}")


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


def _change_task_priority(task: Task, priority: int) -> None:
    """Common function for changing a tasks priority"""
    from app.Controllers import UserController

    with session_scope():
        if priority > task.priority:
            # task priority is increasing
            NotificationController.push(
                msg=f"{task.label()} task has been escalated.",
                user_ids=UserController.all_user_ids(task.org_id)
            )

        task.priority = priority
        task.priority_changed_at = datetime.datetime.utcnow()

    logger.info(f"Changed task {task.id} priority to {priority}")


def _drop(task: Task, req_user: User) -> None:
    """Drops a task"""
    from app.Controllers import UserController
    _unassign_task(task, req_user)

    _transition_task(
        task=task,
        status=TaskStatuses.READY,
        req_user=req_user
    )

    NotificationController.push(
        msg=f"{task.label()} has been dropped.",
        user_ids=UserController.all_user_ids(req_user.org_id)
    )

    req_user.log(
        operation=Operations.DROP,
        resource=Resources.TASK,
        resource_id=task.id
    )
    logger.info(f"User {req_user.id} dropped task {task.id} "
                f"which was assigned to {task.assignee}.")


class TaskController(object):
    @staticmethod
    def task_exists(task_id: int, org_id: int) -> bool:
        """Checks to see if a task exists. """
        with session_scope() as session:
            return session.query(exists().where(and_(Task.id == task_id, Task.org_id == org_id))).scalar()

    @staticmethod
    def task_status_exists(task_status: str) -> bool:
        """Checks to see if a task status exists. """
        with session_scope() as session:
            ret = session.query(exists().where(TaskStatus.status == task_status)).scalar()
        return ret

    @staticmethod
    def task_priority_exists(task_priority: int) -> bool:
        """Checks to see if a task priority exists. """
        with session_scope() as session:
            ret = session.query(exists().where(TaskPriority.priority == task_priority)).scalar()
        return ret

    @staticmethod
    def get_task_by_id(task_id: int, org_id: int) -> Task:
        """Gets a task by its id """
        # TODO I don't think we need the org_id as a param here
        with session_scope() as session:
            ret = session.query(Task).filter_by(
                id=task_id,
                org_id=org_id
            ).first()
        if ret is None:
            logger.info(f"Task with id {task_id} does not exist.")
            raise ValueError(f"Task with id {task_id} does not exist.")
        else:
            return ret

    @staticmethod
    def get_task_priorities(req: request) -> Response:
        """Returns all task priorities """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import TaskPriority

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK_PRIORITIES
        )

        with session_scope() as session:
            task_pr_qry = session.query(TaskPriority).all()

        task_priorities = [tp.as_dict() for tp in task_pr_qry]
        logger.debug(f"Found {len(task_priorities)} task_priorities.")
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_PRIORITIES
        )
        return j_response(task_priorities)

    @staticmethod
    def get_task_statuses(req: request) -> Response:
        """Returns all task statuses """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import TaskStatus

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK_STATUSES
        )

        with session_scope() as session:
            task_st_qry = session.query(TaskStatus).all()

        task_statuses = [ts.as_dict() for ts in task_st_qry if ts.status not in ["DELAYED", "CANCELLED"]]
        logger.debug(f"Found {len(task_statuses)} task statuses.")
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_STATUSES
        )
        return j_response(task_statuses)

    @staticmethod
    def get_task(task_id: int, req: request) -> Response:
        """Get a single task by its id """
        from app.Controllers import TaskController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK
        )

        try:
            task = TaskController.get_task_by_id(task_id, req_user.org_id)
            req_user.log(
                operation=Operations.GET,
                resource=Resources.TASK,
                resource_id=task.id
            )
            return j_response(task.fat_dict())
        except ValueError:
            logger.info(f"Task with id {task_id} does not exist.")
            return g_response("Task does not exist.", 400)

    @staticmethod
    def get_tasks(req: request) -> Response:
        """Get all tasks in an organisation """
        from app.Controllers import AuthorizationController, AuthenticationController, ValidationController
        from app.Models import Task

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASKS
        )

        # start_period, end_period = ValidationController.validate_time_period(req.get_json())
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
        return j_response(tasks)

    @staticmethod
    def create_task(req: request) -> Response:
        """Creates a task"""
        from app.Controllers import ValidationController, AuthenticationController, UserController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.CREATE,
            resource=Resources.TASK,
        )

        task_attrs = ValidationController.validate_create_task_request(req_user.org_id, req.get_json())

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
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.ASSIGN,
                resource=Resources.TASK,
                affected_user_id=task_attrs.get('assignee')
            )

            _assign_task(
                task=task,
                assignee=task_attrs.get('assignee'),
                req_user=req_user
            )
        else:
            NotificationController.push(
                msg=f"{task.label()} task has been created.",
                user_ids=UserController.all_user_ids(req_user.org_id)
            )

        return g_response("Successfully created task", 201)

    @staticmethod
    def update_task(req: request) -> Response:
        """Update a task """
        from app.Controllers import ValidationController, TaskController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.UPDATE,
            resource=Resources.TASK
        )

        task_attrs = ValidationController.validate_update_task_request(req_user.org_id, req.get_json())

        # update the task
        task_to_update = TaskController.get_task_by_id(task_attrs.get('id'), req_user.org_id)

        # if the assignee isn't the same as before then assign someone to it, if the new assignee is null or
        # omitted from the request, then assign the task
        assignee = task_attrs.pop('assignee', None)
        if task_to_update.assignee != assignee:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.ASSIGN,
                resource=Resources.TASK,
                affected_user_id=assignee
            )

            if assignee is None:
                _unassign_task(
                    task=task_to_update,
                    req_user=req_user
                )
            else:
                _assign_task(
                    task=task_to_update,
                    assignee=assignee,
                    req_user=req_user
                )

        # transition
        task_status = task_attrs.pop('status')
        if task_to_update.status != task_status:
            _transition_task(
                task=task_to_update,
                status=task_status,
                req_user=req_user
            )

        # change priority
        task_priority = task_attrs.pop('priority')
        if task_to_update.priority != task_priority:
            _change_task_priority(
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
        return g_response(status=204)

    @staticmethod
    def assign_task(req: request) -> Response:
        """Assigns a user to task """
        from app.Controllers import ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        task, assignee_id = ValidationController.validate_assign_task(req_user.org_id, req.get_json())

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.ASSIGN,
            resource=Resources.TASK,
            affected_user_id=assignee_id
        )

        _assign_task(
            task=task,
            assignee=assignee_id,
            req_user=req_user
        )

        return g_response(status=204)

    @staticmethod
    def drop_task(task_id, req: request = None, req_user: User = None) -> Response:
        """
        Drops a task, which sets it to READY and removes the assignee
        if the task is IN_PROGRESS and has an assignee
        """
        from app.Controllers import ValidationController, AuthenticationController

        if req_user is None:
            req_user = AuthenticationController.get_user_from_request(req.headers)

        task_to_drop = ValidationController.validate_drop_task(req_user.org_id, task_id)

        _drop(task_to_drop, req_user)

        return g_response(status=204)

    @staticmethod
    def cancel_task(task_id, req: request) -> Response:
        """Cancels a task """
        from app.Controllers import ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        task_to_cancel = ValidationController.validate_cancel_task(req_user.org_id, task_id)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.CANCEL,
            resource=Resources.TASK,
            affected_user_id=task_to_cancel.assignee
        )

        _transition_task(
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
            NotificationController.push(
                msg=f"{task_to_cancel.label()} cancelled.",
                user_ids=task_to_cancel.assignee
            )
        logger.info(f"User {req_user.id} cancelled task {task_to_cancel.id}")
        return g_response(status=204)

    @staticmethod
    def transition_task(req: request) -> Response:
        """Transitions the status of a task """
        from app.Controllers import ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        task, task_status = ValidationController.validate_transition_task(req_user.org_id, request.get_json())

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.TRANSITION,
            resource=Resources.TASK,
            affected_user_id=task.assignee
        )

        _transition_task(
            task=task,
            status=task_status,
            req_user=req_user
        )
        return g_response(status=204)

    @staticmethod
    def get_available_transitions(task_id: int, req: request) -> Response:
        """Returns the statuses that a task could be transitioned to, based on the state of the task. """
        from app.Controllers import ValidationController, AuthenticationController
        from app.Models import TaskStatus
        from app.Models.Enums import TaskStatuses

        req_user = AuthenticationController.get_user_from_request(req.headers)

        task = ValidationController.validate_get_transitions(req_user.org_id, task_id)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK_TRANSITIONS
        )

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

        return j_response(ret)

    @staticmethod
    def delay_task(req: request) -> Response:
        """Delays a task """
        from app.Controllers import ValidationController, AuthenticationController
        from app.Models import DelayedTask

        req_user = AuthenticationController.get_user_from_request(req.headers)

        task, delay_for, reason = ValidationController.validate_delay_task_request(req_user.org_id, request.get_json())

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.DELAY,
            resource=Resources.TASK,
            affected_user_id=task.assignee
        )

        with session_scope() as session:
            # transition a task to delayed
            _transition_task(
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
            NotificationController.push(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.created_by
            )
        elif req_user.id == task.created_by:
            NotificationController.push(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.assignee
            )

        req_user.log(
            operation=Operations.DELAY,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"User {req_user.id} delayed task {task.id} for {delay_for}s.")
        return g_response(status=204)

    @staticmethod
    def get_delayed_task(task_id: int, req: request) -> Response:
        """Returns the delayed info for a task """
        from app.Controllers import TaskController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK
        )

        try:
            # get the task
            task = TaskController.get_task_by_id(task_id, req_user.org_id)
            req_user.log(
                operation=Operations.GET,
                resource=Resources.TASK,
                resource_id=task.id
            )
            # if the task has been delayed return the delay info, otherwise return a validation error because the
            # task hasn't been delayed before.
            if task.has_been_delayed():
                return j_response(task.delayed_info())
            else:
                raise ValidationError("Task has not been delayed before.")
        except ValueError as e:
            return g_response(str(e), 400)

    @staticmethod
    def get_task_activity(task_identifier: int, req: request) -> Response:
        """Returns the activity for a task """
        from app.Controllers import TaskController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK_ACTIVITY
        )

        plan_limits = subscription_api.get_limits(req_user.orgs.chargebee_subscription_id)
        activity_log_history_limit = plan_limits.get('task_activity_log_history', 7)

        try:
            # get the task
            task = TaskController.get_task_by_id(task_identifier, req_user.org_id)
            req_user.log(
                operation=Operations.GET,
                resource=Resources.TASK_ACTIVITY,
                resource_id=task.id
            )
            logger.info(f"Getting activity for task with id {task.id}")
            return j_response(task.activity(activity_log_history_limit))
        except ValueError as e:
            return g_response(str(e), 400)

    @staticmethod
    def change_priority(req: request) -> Response:
        """ Change a tasks priority """
        from app.Controllers import TaskController

        request_body = req.get_json()
        params = {
            "org_id": request_body.get('org_id'),
            "task_id": request_body.get('task_id'),
            "priority": request_body.get('priority'),
        }
        for k, v in params.items():
            if v is None:
                raise ValidationError(f"Missing {k} from request")

        task = TaskController.get_task_by_id(params['task_id'], params['org_id'])
        _change_task_priority(
            task=task,
            priority=params['priority']
        )
        return j_response()
