import json
from app import logger, session_scope, g_response
from app.Models import TaskType
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists, and_


class TaskController(object):
    @staticmethod
    def task_type_exists(task_type: str, org_identifier: int) -> bool:
        """
        Checks to see if a task type exists.
        :param task_type:       The task type
        :param org_identifier:  The org id
        :return:                True if the task type exists or false
        """
        with session_scope() as session:
            ret = session.query(exists().where(
                and_(
                    TaskType.type == task_type,
                    TaskType.org_id == org_identifier
                )
            )).scalar()
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

            logger.debug(f"retrieved {len(task_priorities)} task_priorities: {json.dumps(task_priorities)}")
            return Response(json.dumps(task_priorities), status=200, headers={"Content-Type": "application/json"})

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

            logger.debug(f"retrieved {len(task_statuses)} task statuses: {json.dumps(task_statuses)}")
            return Response(json.dumps(task_statuses), status=200, headers={"Content-Type": "application/json"})

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

            logger.debug(f"retrieved {len(task_types)} task types: {json.dumps(task_types)}")
            return Response(json.dumps(task_types), status=200, headers={"Content-Type": "application/json"})

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
            resource_org_id=valid_tt.org_id
        )

        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            with session_scope() as session:
                task_type = TaskType(
                    type=valid_tt.type,
                    org_id=valid_tt.org_id
                )
                session.add(task_type)
            req_user.log(
                operation=Operation.CREATE,
                resource=Resource.TASK_TYPE,
                resource_id=task_type.id
            )
            logger.debug(f"created task type {task_type.as_dict()}")
            return g_response("Successfully created task type", 201)
