import datetime
import json
import typing
from app import logger, session_scope, g_response, j_response
from app.Controllers import AuthController
from app.Models import TaskType, User, Task, TaskStatus, TaskPriority
from app.Models.Enums import TaskStatuses
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists, and_
from sqlalchemy.orm import aliased


def _make_task_dict(
    t: Task,
    ta: typing.Optional[User],
    tcb: User,
    ts: TaskStatus,
    tt: TaskType,
    tp: TaskPriority
) -> dict:
    """
    Creates a nice dict of a task
    :param t:   The task
    :param ta:  The task assignee
    :param tcb: The task created by
    :param ts:  The task status
    :param tt:  The task type
    :param tp:  The task priority
    :return:    A dict
    """
    extras = {
        'assignee': ta.as_dict() if ta is not None else None,
        'created_by': tcb.as_dict(),
        'status': ts.as_dict(),
        'type': tt.as_dict(),
        'priority': tp.as_dict()
    }

    task_dict = t.as_dict()

    # remove extras from base task
    for k in extras:
        task_dict.pop(k)

    # convert datetimes to str
    for k, v in task_dict.items():
        if isinstance(v, datetime.datetime):
            task_dict[k] = v.strftime("%Y-%m-%dT%H:%M:%S%z")

    return dict(sorted({
        **task_dict,
        **extras
    }.items()))


class TaskController(object):
    @staticmethod
    def get_assignee(task_id: int) -> typing.Union[None, int]:
        """
        Gets the assignee for a task
        :param task_id:     The id of the task
        :return:            The assignee's user id, or None
        """
        with session_scope() as session:
            ret = session.query(Task).filter(Task.id == task_id).first()
        if ret is None:
            logger.info(f"No-one is assigned to task with id {task_id}")
            raise ValueError(f"No-one is assigned to task with id {task_id}")
        else:
            return ret.assignee

    @staticmethod
    def get_task_by_id(task_id: int) -> Task:
        """
        Gets a task by its id
        :param task_id:         The tasks's id
        :raises ValueError:     If the task doesn't exist.
        :return:                The Task
        """
        with session_scope() as session:
            ret = session.query(Task).filter(Task.id == task_id).first()
        if ret is None:
            logger.info(f"Task with id {task_id} does not exist.")
            raise ValueError(f"Task with id {task_id} does not exist.")
        else:
            return ret

    @staticmethod
    def task_exists(task_id: int) -> bool:
        """
        Checks to see if a task type exists.
        :param task_id:       The task id or type
        :return:              True if the task type exists or false
        """
        with session_scope() as session:
            return session.query(exists().where(Task.id == task_id)).scalar()

    @staticmethod
    def task_type_exists(task_type_identifier: typing.Union[str, int], org_identifier: int) -> bool:
        """
        Checks to see if a task type exists.
        :param task_type_identifier:       The task id or type
        :param org_identifier:  The org id
        :return:                True if the task type exists or false
        """
        with session_scope() as session:
            if isinstance(task_type_identifier, int):
                logger.info(f"task type identifer is an int so finding by id")
                return session.query(exists().where(
                    and_(
                        TaskType.id == task_type_identifier,
                        TaskType.org_id == org_identifier
                    )
                )).scalar()
            elif isinstance(task_type_identifier, str):
                logger.info(f"task type identifer is a str so finding by type")
                return session.query(exists().where(
                    and_(
                        TaskType.type == task_type_identifier,
                        TaskType.org_id == org_identifier
                    )
                )).scalar()

    @staticmethod
    def task_status_exists(task_status: str) -> bool:
        """
        Checks to see if a task type exists.
        :param task_status:     The task status
        :return:                True if the task status exists or false
        """
        with session_scope() as session:
            ret = session.query(exists().where(TaskStatus.status == task_status)).scalar()
        return ret

    @staticmethod
    def task_priority_exists(task_priority: int) -> bool:
        """
        Checks to see if a task type exists.
        :param task_priority:       The task priority
        :return:                    True if the task priority exists or false
        """
        with session_scope() as session:
            ret = session.query(exists().where(TaskPriority.priority == task_priority)).scalar()
        return ret

    @staticmethod
    def get_task_priorities(request: request) -> Response:
        from app.Controllers import AuthController
        from app.Models import User
        from app.Models import TaskPriority

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.GET,
            resource=Resource.TASK_PRIORITY
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            with session_scope() as session:
                task_pr_qry = session.query(TaskPriority).all()

            task_priorities = [tp.as_dict() for tp in task_pr_qry]

            logger.info(f"retrieved {len(task_priorities)} task_priorities: {json.dumps(task_priorities)}")
            return j_response(task_priorities)

    @staticmethod
    def get_task_statuses(request: request) -> Response:
        from app.Controllers import AuthController
        from app.Models import User
        from app.Models import TaskStatus

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.GET,
            resource=Resource.TASK_STATUS
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            with session_scope() as session:
                task_st_qry = session.query(TaskStatus).all()

            task_statuses = [ts.as_dict() for ts in task_st_qry]

            logger.info(f"retrieved {len(task_statuses)} task statuses: {json.dumps(task_statuses)}")
            return j_response(task_statuses)

    @staticmethod
    def get_task_types(request: request) -> Response:
        from app.Controllers import AuthController
        from app.Models import User
        from app.Models import TaskType

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.GET,
            resource=Resource.TASK_TYPE
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            with session_scope() as session:
                task_tt_qry = session.query(TaskType).filter(TaskType.org_id == req_user.org_id).all()

            task_types = [tt.as_dict() for tt in task_tt_qry]

            logger.info(f"retrieved {len(task_types)} task types: {json.dumps(task_types)}")
            return j_response(task_types)

    @staticmethod
    def create_task_types(request: request) -> Response:
        from app.Controllers import AuthController, ValidationController
        from app.Models import User
        from app.Models import TaskType

        request_body = request.get_json()

        # validate task_type
        valid_tt = ValidationController.validate_create_task_type_request(request_body)

        if isinstance(valid_tt, Response):
            return valid_tt

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.CREATE,
            resource=Resource.TASK_TYPE,
            resource_org_id=valid_tt.get('org_id')
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            with session_scope() as session:
                task_type = TaskType(
                    type=valid_tt.get('type'),
                    org_id=valid_tt.get('org_id')
                )
                session.add(task_type)
            req_user.log(
                operation=Operation.CREATE,
                resource=Resource.TASK_TYPE,
                resource_id=task_type.id
            )
            logger.info(f"created task type {task_type.as_dict()}")
            return g_response("Successfully created task type", 201)

    @staticmethod
    def task_create(request: request) -> Response:
        """
        Creates a task
        :param request: The request
        :return:        A response
        """
        def create_task(valid_task: dict, req_user: User) -> Response:
            """
            Creates the task
            :param valid_task:  The validated task dict
            :param req_user:    The user making the request
            :return:            Response
            """
            with session_scope() as session:
                task = Task(
                    org_id=valid_task.get('org_id'),
                    type=valid_task.get('type'),
                    description=valid_task.get('description'),
                    status=valid_task.get('status'),
                    time_estimate=valid_task.get('time_estimate'),
                    due_time=valid_task.get('due_time'),
                    assignee=valid_task.get('assignee'),
                    priority=valid_task.get('priority'),
                    created_by=req_user.id,
                    created_at=valid_task.get('created_at'),
                    finished_at=valid_task.get('finished_at')
                )
                session.add(task)

            req_user.log(
                operation=Operation.CREATE,
                resource=Resource.TASK,
                resource_id=task.id
            )
            if task.assignee is not None:
                req_user.log(
                    operation=Operation.ASSIGN,
                    resource=Resource.TASK,
                    resource_id=task.id
                )
                logger.info(f'Assigned user id {task.assignee} to task id {task.id}')
            logger.info(f"created task {task.as_dict()}")
            return g_response("Successfully created task", 201)

        request_body = request.get_json()

        # validate task
        from app.Controllers import ValidationController
        valid_task = ValidationController.validate_create_task_request(request_body)

        # response is a failure
        if isinstance(valid_task, Response):
            return valid_task

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.CREATE,
            resource=Resource.TASK,
            resource_org_id=valid_task.get('org_id')
        )
        # no auth
        if isinstance(req_user, Response):
            return req_user

        # optionally authorize assigning if an assignee was set
        if valid_task.get('assignee') is not None:
            req_user = AuthController.authorize_request(
                request=request,
                operation=Operation.ASSIGN,
                resource=Resource.TASK,
                resource_org_id=valid_task.get('org_id'),
                resource_user_id=valid_task.get('assignee')
            )
            # no auth
            if isinstance(req_user, Response):
                return req_user

        return create_task(valid_task, req_user=req_user)

    @staticmethod
    def task_update(task_id: int, request: request) -> Response:
        """
        Updates a task. Requires the full task object in the request.
        :param task_id: The task ID
        :param request:
        :return:
        """
        from app.Controllers import ValidationController, TaskController
        request_body = request.get_json()

        try:
            task_id = int(task_id)
        except ValueError:
            return g_response(f"cannot cast `{task_id}` to int", 400)

        valid_task = ValidationController.validate_update_task_request(task_id, request_body)

        if isinstance(valid_task, Response):
            return valid_task

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.UPDATE,
            resource=Resource.TASK,
            resource_org_id=valid_task.get('org_id'),
        )
        # no auth
        if isinstance(req_user, Response):
            return req_user

        # optionally authorize assigning if an assignee was set
        if valid_task.get('assignee') is not None:
            req_user = AuthController.authorize_request(
                request=request,
                operation=Operation.ASSIGN,
                resource=Resource.TASK,
                resource_org_id=valid_task.get('org_id'),
                resource_user_id=valid_task.get('assignee')
            )
            # no auth
            if isinstance(req_user, Response):
                return req_user

        # update the task
        task_to_update = TaskController.get_task_by_id(task_id)

        with session_scope():
            for k, v in valid_task.items():
                task_to_update.__setattr__(k, v)

            req_user.log(
                operation=Operation.UPDATE,
                resource=Resource.TASK,
                resource_id=task_id
            )

        logger.info(f"updated task {task_to_update.as_dict()}")
        return g_response(status=204)

    @staticmethod
    def task_get_all(request: request) -> Response:
        """
        Get all users
        :param request:     The request object
        :return:
        """
        from app.Controllers import AuthController
        from app.Models import Task

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.GET,
            resource=Resource.TASK
        )

        # no auth
        if isinstance(req_user, Response):
            return req_user

        with session_scope() as session:
            task_assignee, task_created_by = aliased(User), aliased(User)

            tasks_qry = session.query(Task, task_assignee, task_created_by, TaskStatus, TaskType, TaskPriority)\
                .outerjoin(task_assignee, task_assignee.id == Task.assignee)\
                .join(task_created_by, task_created_by.id == Task.created_by)\
                .join(Task.created_bys)\
                .join(Task.task_statuses)\
                .join(Task.task_types)\
                .join(Task.task_priorities)\
                .filter(Task.org_id == req_user.org_id)\
                .all()

        tasks = [_make_task_dict(t, ta, tcb, ts, tt, tp) for t, ta, tcb, ts, tt, tp in tasks_qry]

        logger.info(f"retrieved {len(tasks)} users: {json.dumps(tasks)}")
        return j_response(tasks)

    @staticmethod
    def assign_task(request: request) -> Response:
        """
        Assigns a user to task
        :param request:
        :return:
        """
        from app.Controllers import ValidationController, TaskController
        request_body = request.get_json()

        valid_assignment = ValidationController.validate_assign_task(request_body)

        # invalid
        if isinstance(valid_assignment, Response):
            return valid_assignment

        req_user = AuthController.authorize_request(
            request=request,
            operation=Operation.ASSIGN,
            resource=Resource.TASK,
            resource_org_id=valid_assignment.get('org_id'),
            resource_user_id=valid_assignment.get('assignee')
        )

        if isinstance(req_user, Response):
            return req_user

        task_to_assign = TaskController.get_task_by_id(valid_assignment.get('task_id'))

        with session_scope():
            task_to_assign.assignee = valid_assignment.get('assignee')

        return g_response(status=204)

    @staticmethod
    def drop_task(task_id, _request: request) -> Response:
        """
        Assigns a user to task
        :param _request:
        :return:
        """
        from app.Controllers import ValidationController, TaskController

        try:
            task_id = int(task_id)
        except ValueError:
            return g_response(f"cannot cast `{task_id}` to int", 400)

        valid_task_drop = ValidationController.validate_drop_task(task_id)

        # invalid
        if isinstance(valid_task_drop, Response):
            return valid_task_drop

        req_user = AuthController.authorize_request(
            request=_request,
            operation=Operation.DROP,
            resource=Resource.TASK,
            resource_org_id=valid_task_drop.get('org_id'),
            resource_user_id=valid_task_drop.get('assignee')
        )

        if isinstance(req_user, Response):
            return req_user

        task_to_drop = TaskController.get_task_by_id(valid_task_drop.get('task_id'))

        with session_scope():
            task_to_drop.assignee = None
            task_to_drop.status = TaskStatuses.READY

        return g_response(status=204)
