from flask import Response
from flask_restplus import Namespace

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import TaskStatus
from app.Models.Enums import Operations, Resources
from app.Models.Response import get_task_statuses_response_dto

task_statuses_route = Namespace(
    path="/tasks/statuses",
    name="Tasks",
    description="Manage tasks"
)


@task_statuses_route.route('/')
class TaskStatuses(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_STATUSES)
    @task_statuses_route.response(200, "Success", get_task_statuses_response_dto)
    def get(self, **kwargs) -> Response:
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
