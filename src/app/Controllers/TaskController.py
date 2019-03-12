import json
import typing
from app import logger, session_scope, g_response, j_response
from app.Controllers import AuthController
from app.Models import TaskType, User, Task, TaskStatus, TaskPriority
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists, and_


class TaskController(object):
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
