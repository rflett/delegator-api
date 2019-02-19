import json
import typing
from app.Models.RBAC import Role, Operation, Resource
from app.Models.RBAC.Permission import Permission
from app import logger, session_scope
from flask import request, Response


class TaskController(object):
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
