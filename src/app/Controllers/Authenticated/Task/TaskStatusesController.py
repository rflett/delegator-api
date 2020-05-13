from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models.Dao import TaskStatus
from app.Models.Enums import Operations, Resources

api = Namespace(path="/tasks/statuses", name="Tasks", description="Manage tasks")


@api.route("/")
class TaskStatuses(RequestValidationController):
    # TODO can be removed if unused in mobile app

    statuses = ["SCHEDULED", "READY", "IN_PROGRESS", "DELAYED", "COMPLETED", "CANCELLED"]
    task_status_dto = api.model(
        "Task Status",
        {
            "status": fields.String(enum=statuses),
            "label": fields.String(),
            "disabled": fields.Boolean(),
            "tooltip": fields.String(),
        },
    )
    response_dto = api.model("Get Task Statuses Response", {"statuses": fields.List(fields.Nested(task_status_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_STATUSES)
    @api.marshal_with(response_dto, code=200)
    def get(self, **kwargs):
        """Returns all task statuses """
        req_user = kwargs["req_user"]

        with session_scope() as session:
            task_status_qry = session.query(TaskStatus).all()

        task_statuses = [ts.as_dict() for ts in task_status_qry]
        req_user.log(Operations.GET, Resources.TASK_STATUSES)
        return {"statuses": task_statuses}, 200
