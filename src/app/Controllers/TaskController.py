import datetime
import json

from flask import request, Response
from sqlalchemy import exists, and_
from sqlalchemy.orm import aliased

from app import logger, session_scope, g_response, j_response
from app.Exceptions import AuthorizationError, AuthenticationError
from app.Controllers import AuthorizationController
from app.Models import User, Task, TaskStatus, TaskPriority, DelayedTask, Notification, TaskType
from app.Models.Enums import TaskStatuses, Events
from app.Models.RBAC import Operation, Resource


def _transition_task(task: Task, status: str, req_user: User) -> None:
    """ Common function for transitioning a task """
    with session_scope() as session:
        old_status = task.status

        if status == old_status:
            return

        # remove delayed task
        if old_status == TaskStatuses.DELAYED and status != TaskStatuses.DELAYED:
            delayed_task = session.query(DelayedTask).filter(DelayedTask.task_id == task.id).first()
            delayed_task.expired = datetime.datetime.utcnow()

        # finished task
        if status == TaskStatuses.COMPLETED:
            task.finished_by = req_user.id
            task.finished_at = datetime.datetime.utcnow()

        # start task once
        if status == TaskStatuses.INPROGRESS and task.started_at is not None:
            task.started_at = datetime.datetime.utcnow()

        task.status = status
        task.status_changed_at = datetime.datetime.utcnow()

    Notification(
        org_id=task.org_id,
        event=f'task_transitioned_{task.status.lower()}',
        event_id=task.id,
        event_friendly=f"Transitioned from {old_status.lower()} to {status.lower()}."
    ).publish()
    Notification(
        org_id=req_user.org_id,
        event=Events.user_transitioned_task,
        event_id=req_user.id,
        event_friendly=f"Transitioned {task.label()} from {old_status.lower()} to {status.lower()}."
    ).publish()
    req_user.log(
        operation=Operation.TRANSITION,
        resource=Resource.TASK,
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
        operation=Operation.ASSIGN,
        resource=Resource.TASK,
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
            operation=Operation.ASSIGN,
            resource=Resource.TASK,
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

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.GET,
                resource=Resource.TASK_PRIORITIES
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        with session_scope() as session:
            task_pr_qry = session.query(TaskPriority).all()

        task_priorities = [tp.as_dict() for tp in task_pr_qry]
        logger.debug(f"found {len(task_priorities)} task_priorities: {json.dumps(task_priorities)}")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASK_PRIORITIES
        )
        return j_response(task_priorities)

    @staticmethod
    def get_task_statuses(req: request) -> Response:
        """ Returns all task statuses """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import TaskStatus
        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.GET,
                resource=Resource.TASK_STATUSES
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        with session_scope() as session:
            task_st_qry = session.query(TaskStatus).all()

        task_statuses = [ts.as_dict() for ts in task_st_qry]
        logger.debug(f"found {len(task_statuses)} task statuses: {json.dumps(task_statuses)}")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASK_STATUSES
        )
        return j_response(task_statuses)

    @staticmethod
    def get_task(task_id: int, req: request) -> Response:
        """ Get a single task. """
        from app.Controllers import TaskController, AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.GET,
                resource=Resource.TASK
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        try:
            task = TaskController.get_task_by_id(task_id, req_user.org_id)
            logger.debug(f"found task {task.fat_dict()}")
            req_user.log(
                operation=Operation.GET,
                resource=Resource.TASK,
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

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.GET,
                resource=Resource.TASKS
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        with session_scope() as session:
            task_assignee, task_created_by = aliased(User), aliased(User)
            tasks_qry = session.query(Task, task_assignee, task_created_by, TaskStatus, TaskType, TaskPriority) \
                .outerjoin(task_assignee, task_assignee.id == Task.assignee) \
                .join(task_created_by, task_created_by.id == Task.created_by) \
                .join(Task.created_bys) \
                .join(Task.task_statuses) \
                .join(Task.task_types) \
                .join(Task.task_priorities) \
                .filter(Task.org_id == req_user.org_id) \
                .all()

        tasks = []

        for t, ta, tcb, ts, tt, tp in tasks_qry:
            task_dict = t.as_dict()
            task_dict['assignee'] = ta.as_dict() if ta is not None else None
            task_dict['created_by'] = tcb.as_dict()
            task_dict['status'] = ts.as_dict()
            task_dict['type'] = tt.as_dict()
            task_dict['priority'] = tp.as_dict()
            tasks.append(task_dict)

        logger.debug(f"found {len(tasks)} tasks")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASKS
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

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.CREATE,
                resource=Resource.TASK,
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        task_attrs = ValidationController.validate_create_task_request(req.get_json())
        # invalid
        if isinstance(task_attrs, Response):
            return task_attrs

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
            operation=Operation.CREATE,
            resource=Resource.TASK,
            resource_id=task.id
        )
        logger.info(f"created task {task.as_dict()}")

        # optionally assign the task
        if task_attrs.get('assignee') is not None:
            try:
                AuthorizationController.authorize_request(
                    auth_user=req_user,
                    operation=Operation.ASSIGN,
                    resource=Resource.TASK,
                    affected_user_id=task_attrs.get('assignee')
                )
            except AuthorizationError as e:
                return g_response(str(e), 400)

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

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.UPDATE,
                resource=Resource.TASK
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        task_attrs = ValidationController.validate_update_task_request(req_user.org_id, req.get_json())
        # invalid task
        if isinstance(task_attrs, Response):
            return task_attrs

        # update the task
        task_to_update = TaskController.get_task_by_id(task_attrs.get('id'), req_user.org_id)

        # assigning
        assignee = task_attrs.pop('assignee', None)
        if task_to_update.assignee != assignee:
            try:
                AuthorizationController.authorize_request(
                    auth_user=req_user,
                    operation=Operation.ASSIGN,
                    resource=Resource.TASK,
                    affected_user_id=assignee
                )
            except AuthorizationError as e:
                return g_response(str(e), 400)

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
            operation=Operation.UPDATE,
            resource=Resource.TASK,
            resource_id=task_to_update.id
        )
        logger.info(f"updated task {task_to_update.as_dict()}")
        return g_response(status=204)

    @staticmethod
    def assign_task(req: request) -> Response:
        """ Assigns a user to task """
        from app.Controllers import ValidationController, AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        valid_assignment = ValidationController.validate_assign_task(req_user.org_id, req.get_json())
        # invalid assignment
        if isinstance(valid_assignment, Response):
            return valid_assignment
        else:
            task, assignee_id = valid_assignment

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.ASSIGN,
                resource=Resource.TASK,
                affected_user_id=assignee_id
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

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

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        task_to_drop = ValidationController.validate_drop_task(req_user.org_id, task_id)
        # invalid task drop request
        if isinstance(task_to_drop, Response):
            return task_to_drop

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.DROP,
                resource=Resource.TASK,
                affected_user_id=task_to_drop.assignee
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        _unassign_task(task_to_drop, req_user)
        _transition_task(
            task=task_to_drop,
            status=TaskStatuses.READY,
            req_user=req_user
        )
        req_user.log(
            operation=Operation.DROP,
            resource=Resource.TASK,
            resource_id=task_id
        )
        logger.info(f"user {req_user.id} dropped task {task_to_drop.id} "
                    f"which was assigned to {task_to_drop.assignee}")
        return g_response(status=204)

    @staticmethod
    def transition_task(req: request) -> Response:
        """ Transitions the status of a task """
        from app.Controllers import ValidationController, AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        valid_task_transition = ValidationController.validate_transition_task(req_user.org_id, request.get_json())
        # invalid
        if isinstance(valid_task_transition, Response):
            return valid_task_transition
        else:
            task, task_status = valid_task_transition

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.TRANSITION,
                resource=Resource.TASK,
                affected_user_id=task.assignee
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        _transition_task(
            task=task,
            status=task_status,
            req_user=req_user
        )

        return g_response(status=204)

    @staticmethod
    def delay_task(req: request) -> Response:
        """ Transitions the status of a task """
        from app.Controllers import ValidationController, AuthenticationController
        from app.Models import DelayedTask

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        validate_res = ValidationController.validate_delay_task_request(req_user.org_id, request.get_json())
        # invalid
        if isinstance(validate_res, Response):
            return validate_res
        else:
            task, delay_for = validate_res

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.DELAY,
                resource=Resource.TASK,
                affected_user_id=task.assignee
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

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
            else:
                delayed_task = DelayedTask(
                    task_id=task.id,
                    delay_for=delay_for,
                    delayed_at=datetime.datetime.utcnow(),
                    delayed_by=req_user.id
                )
                session.add(delayed_task)

        req_user.log(
            operation=Operation.DELAY,
            resource=Resource.TASK,
            resource_id=task.id
        )
        logger.info(f"user {req_user.id} delayed task {task.id} for {delay_for}")
        return g_response(status=204)

    @staticmethod
    def get_task_activity(task_identifier: int, req: request) -> Response:
        """ Returns the activity for a user """
        from app.Controllers import TaskController, AuthenticationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.GET,
                resource=Resource.TASK_ACTIVITY
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        try:
            task = TaskController.get_task_by_id(task_identifier, req_user.org_id)
            req_user.log(
                operation=Operation.GET,
                resource=Resource.TASK_ACTIVITY,
                resource_id=task.id
            )
            logger.info(f"getting activity for task with id {task.id}")
            return j_response(task.activity())
        except ValueError as e:
            return g_response(str(e), 400)
