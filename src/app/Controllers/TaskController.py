import datetime
import json

from flask import request, Response
from sqlalchemy import exists, and_
from sqlalchemy.orm import aliased

from app import logger, session_scope, g_response, j_response
from app.Exceptions import ValidationError
from app.Controllers import AuthorizationController
from app.Models import User, Task, TaskStatus, TaskPriority, DelayedTask, Notification, TaskType
from app.Models.Enums import TaskStatuses, Events, Operations, Resources


def _pretty_status_label(status: str) -> str:
    """ Converts a task status from IN_PROGRESS to 'In Progress' """
    if "_" in status:
        words = status.lower().split('_')
        return " ".join([w.capitalize() for w in words])
    else:
        return status.lower().capitalize()


def _transition_task(task: Task, status: str, req_user: User) -> None:
    """ Common function for transitioning a task """
    with session_scope() as session:
        old_status = task.status

        if status == old_status:
            return

        if old_status == TaskStatuses.READY and task.assignee is None and status != TaskStatuses.CANCELLED:
            raise ValidationError("Cannot move task out of ready because it's not assigned to anyone.")

        # remove delayed task
        if old_status == TaskStatuses.DELAYED and status != TaskStatuses.DELAYED:
            delayed_task = session.query(DelayedTask).filter(DelayedTask.task_id == task.id).first()
            delayed_task.expired = datetime.datetime.utcnow()

        # finished task
        if status == TaskStatuses.COMPLETED:
            task.finished_by = req_user.id
            task.finished_at = datetime.datetime.utcnow()

        # start task once
        if status == TaskStatuses.IN_PROGRESS and task.started_at is None:
            task.started_at = datetime.datetime.utcnow()

        task.status = status
        task.status_changed_at = datetime.datetime.utcnow()

    old_status_label = _pretty_status_label(old_status)
    new_status_label = _pretty_status_label(status)

    Notification(
        org_id=task.org_id,
        event=f'task_transitioned_{task.status.lower()}',
        event_id=task.id,
        event_friendly=f"Transitioned from {old_status_label} to {new_status_label}."
    ).publish()
    Notification(
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
    logger.info(f"user {req_user.id} transitioned task {task.id} from {old_status} to {status}")


def _assign_task(task: Task, assignee: int, req_user: User) -> None:
    """ Common function for assigning a task """
    from app.Controllers import UserController
    with session_scope():
        task.assignee = assignee

    assigned_user = UserController.get_user_by_id(assignee)
    Notification(
        org_id=task.org_id,
        event=Events.task_assigned,
        event_id=task.id,
        event_friendly=f"{assigned_user.name()} assigned to task by {req_user.name()}."
    ).publish()
    Notification(
        org_id=req_user.org_id,
        event=Events.user_assigned_task,
        event_id=req_user.id,
        event_friendly=f"Assigned {assigned_user.name()} to {task.label()}."
    ).publish()
    Notification(
        org_id=assigned_user.org_id,
        event=Events.user_assigned_to_task,
        event_id=assigned_user.id,
        event_friendly=f"Assigned to {task.label()} by {req_user.name()}."
    ).publish()
    req_user.log(
        operation=Operations.ASSIGN,
        resource=Resources.TASK,
        resource_id=task.id
    )
    logger.info(f"assigned task {task.id} to user {assignee}")


def _unassign_task(task: Task, req_user: User) -> None:
    """ Common function for assigning a task """
    from app.Controllers import UserController

    if task.assignee is not None:
        old_assignee = UserController.get_user_by_id(task.assignee)

        with session_scope():
            task.assignee = None

        Notification(
            org_id=task.org_id,
            event=Events.task_unassigned,
            event_id=task.id,
            event_friendly=f"{old_assignee.name()} unassigned from task by {req_user.name()}."
        ).publish()
        Notification(
            org_id=req_user.org_id,
            event=Events.user_unassigned_task,
            event_id=req_user.id,
            event_friendly=f"Unassigned {old_assignee.name()} from {task.label()}."
        ).publish()
        Notification(
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
        logger.info(f"unassigned user {old_assignee.id} from task {task.id}")


def _change_task_priority(org_id: int, task_id: int, priority: int) -> None:
    """ Common function for assigning a task """
    with session_scope():
        task_to_change = TaskController.get_task_by_id(task_id, org_id)
        task_to_change.priority = priority
        task_to_change.priority_changed_at = datetime.datetime.utcnow()

    logger.info(f"changed task {task_id} priority to {priority}")


class TaskController(object):
    @staticmethod
    def task_exists(task_id: int, org_id: int) -> bool:
        """ Checks to see if a task type exists. """
        with session_scope() as session:
            return session.query(exists().where(and_(Task.id == task_id, Task.org_id == org_id))).scalar()

    @staticmethod
    def task_status_exists(task_status: str) -> bool:
        """ Checks to see if a task type exists. """
        with session_scope() as session:
            ret = session.query(exists().where(TaskStatus.status == task_status)).scalar()
        return ret

    @staticmethod
    def task_priority_exists(task_priority: int) -> bool:
        """ Checks to see if a task type exists. """
        with session_scope() as session:
            ret = session.query(exists().where(TaskPriority.priority == task_priority)).scalar()
        return ret

    @staticmethod
    def get_task_by_id(task_id: int, org_id: int) -> Task:
        """ Gets a task by its id """
        with session_scope() as session:
            ret = session.query(Task).filter(and_(Task.id == task_id, Task.org_id == org_id)).first()
        if ret is None:
            logger.info(f"Task with id {task_id} does not exist.")
            raise ValueError(f"Task with id {task_id} does not exist.")
        else:
            return ret

    @staticmethod
    def get_task_priorities(req: request) -> Response:
        """ Returns all task priorities """
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
        logger.debug(f"found {len(task_priorities)} task_priorities: {json.dumps(task_priorities)}")
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_PRIORITIES
        )
        return j_response(task_priorities)

    @staticmethod
    def get_task_statuses(req: request) -> Response:
        """ Returns all task statuses """
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
        logger.debug(f"found {len(task_statuses)} task statuses: {json.dumps(task_statuses)}")
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_STATUSES
        )
        return j_response(task_statuses)

    @staticmethod
    def get_task(task_id: int, req: request) -> Response:
        """ Get a single task. """
        from app.Controllers import TaskController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK
        )

        try:
            task = TaskController.get_task_by_id(task_id, req_user.org_id)
            logger.debug(f"found task {task.fat_dict()}")
            req_user.log(
                operation=Operations.GET,
                resource=Resources.TASK,
                resource_id=task.id
            )
            return j_response(task.fat_dict())
        except ValueError:
            logger.info(f"task with id {task_id} does not exist")
            return g_response("Task does not exist.", 400)

    @staticmethod
    def get_tasks(req: request) -> Response:
        """ Get all users """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import Task

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASKS
        )

        with session_scope() as session:
            task_assignee, task_created_by, task_finished_by = aliased(User), aliased(User), aliased(User)
            tasks_qry = session\
                .query(Task, task_assignee, task_created_by, task_finished_by, TaskStatus, TaskType, TaskPriority) \
                .outerjoin(task_assignee, task_assignee.id == Task.assignee) \
                .outerjoin(task_finished_by, task_finished_by.id == Task.finished_by) \
                .join(task_created_by, task_created_by.id == Task.created_by) \
                .join(Task.created_bys) \
                .join(Task.task_statuses) \
                .join(Task.task_types) \
                .join(Task.task_priorities) \
                .filter(Task.org_id == req_user.org_id) \
                .all()

        tasks = []

        for t, ta, tcb, tfb, ts, tt, tp in tasks_qry:
            task_dict = t.as_dict()
            task_dict['assignee'] = ta.as_dict() if ta is not None else None
            task_dict['created_by'] = tcb.as_dict()
            task_dict['finished_by'] = tfb.as_dict() if tfb is not None else None
            task_dict['status'] = ts.as_dict()
            task_dict['type'] = tt.as_dict()
            task_dict['priority'] = tp.as_dict()
            tasks.append(task_dict)

        logger.debug(f"found {len(tasks)} tasks")
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASKS
        )
        return j_response(tasks)

    @staticmethod
    def create_task(req: request) -> Response:
        """
        Creates a task
        :param req: The request
        :return:        A response
        """
        from app.Controllers import ValidationController, AuthenticationController

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

        Notification(
            org_id=task.org_id,
            event=Events.task_created,
            event_id=task.id,
            event_friendly=f"Created by {req_user.name()}."
        ).publish()
        Notification(
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

        # optionally assign the task
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

        return g_response("Successfully created task", 201)

    @staticmethod
    def update_task(req: request) -> Response:
        """ Updates a task. Requires the full task object in the request. """
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

        # assigning
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
                org_id=req_user.org_id,
                task_id=task_to_update.id,
                priority=task_priority
            )

        # update other values
        with session_scope():
            for k, v in task_attrs.items():
                task_to_update.__setattr__(k, v)

        # publish event
        Notification(
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
        logger.info(f"updated task {task_to_update.as_dict()}")
        return g_response(status=204)

    @staticmethod
    def assign_task(req: request) -> Response:
        """ Assigns a user to task """
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
    def drop_task(task_id, req: request) -> Response:
        """ Drops a task, which sets it to READY and removes the assignee """
        from app.Controllers import ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        task_to_drop = ValidationController.validate_drop_task(req_user.org_id, task_id)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.DROP,
            resource=Resources.TASK,
            affected_user_id=task_to_drop.assignee
        )

        _unassign_task(task_to_drop, req_user)
        _transition_task(
            task=task_to_drop,
            status=TaskStatuses.READY,
            req_user=req_user
        )
        req_user.log(
            operation=Operations.DROP,
            resource=Resources.TASK,
            resource_id=task_id
        )
        logger.info(f"user {req_user.id} dropped task {task_to_drop.id} "
                    f"which was assigned to {task_to_drop.assignee}")
        return g_response(status=204)

    @staticmethod
    def cancel_task(task_id, req: request) -> Response:
        """ Drops a task, which sets it to READY and removes the assignee """
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
        logger.info(f"user {req_user.id} cancelled task {task_to_cancel.id}")
        return g_response(status=204)

    @staticmethod
    def transition_task(req: request) -> Response:
        """ Transitions the status of a task """
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
        """ Transitions the status of a task """
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

        if task.assignee is None:
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY]
            }
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # Enabled options
            ret += [ts.as_dict() for ts in enabled_qry]

            # Disabled options
            ret += [ts.as_dict(disabled=True, tooltip="No one is assigned to this task.") for ts in disabled_qry]

        else:
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY, TaskStatuses.IN_PROGRESS, TaskStatuses.CANCELLED],
                TaskStatuses.IN_PROGRESS: [TaskStatuses.IN_PROGRESS, TaskStatuses.COMPLETED],
                TaskStatuses.DELAYED: [TaskStatuses.DELAYED, TaskStatuses.IN_PROGRESS]
            }
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # Enabled options
            ret += [ts.as_dict() for ts in enabled_qry if ts.status not in ["DELAYED", "CANCELLED"]]

            # Disabled options
            ret += [ts.as_dict(disabled=True) for ts in disabled_qry if ts.status not in ["DELAYED", "CANCELLED"]]

        return j_response(ret)

    @staticmethod
    def delay_task(req: request) -> Response:
        """ Transitions the status of a task """
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
            # set task to delayed
            _transition_task(
                task=task,
                status=TaskStatuses.DELAYED,
                req_user=req_user
            )
            # created delayed until
            delay = session.query(DelayedTask).filter(
                    DelayedTask.task_id == task.id
                ).first()
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

        req_user.log(
            operation=Operations.DELAY,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"user {req_user.id} delayed task {task.id} for {delay_for}")
        return g_response(status=204)

    @staticmethod
    def get_delayed_task(task_id: int, req: request) -> Response:
        """ Returns the activity for a user """
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
            logger.info(f"getting activity for task with id {task.id}")
            if task.has_been_delayed():
                return j_response(task.delayed_info())
            else:
                raise ValidationError("Task has not been delayed before.")
        except ValueError as e:
            return g_response(str(e), 400)

    @staticmethod
    def get_task_activity(task_identifier: int, req: request) -> Response:
        """ Returns the activity for a user """
        from app.Controllers import TaskController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK_ACTIVITY
        )

        try:
            task = TaskController.get_task_by_id(task_identifier, req_user.org_id)
            req_user.log(
                operation=Operations.GET,
                resource=Resources.TASK_ACTIVITY,
                resource_id=task.id
            )
            logger.info(f"getting activity for task with id {task.id}")
            return j_response(task.activity())
        except ValueError as e:
            return g_response(str(e), 400)
