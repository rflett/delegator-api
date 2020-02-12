import datetime
from dateutil import tz

from flask import Response
from flask_restx import Namespace
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from app import session_scope, app
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import User, Task, TaskLabel, TaskType
from app.Models.Enums import Operations, Resources
from app.Models.Response import tasks_response, message_response_dto, min_tasks_response
from app.Services import TaskService

tasks_route = Namespace(path="/tasks", name="Tasks", description="Manage tasks")

task_service = TaskService()


@tasks_route.route("/")
class Tasks(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASKS)
    @tasks_route.response(200, "Success", tasks_response)
    @tasks_route.response(403, "Insufficient privileges", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Get all tasks in an organisation"""
        req_user = kwargs["req_user"]

        # start_period, end_period = self.validate_time_period(req.get_json())
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        # join across all related tables to get full info
        with session_scope() as session:
            task_assignee, task_created_by, task_finished_by = aliased(User), aliased(User), aliased(User)
            tasks_qry = (
                session.query(Task, task_assignee, task_created_by, task_finished_by)
                .outerjoin(task_assignee, task_assignee.id == Task.assignee)
                .outerjoin(task_finished_by, task_finished_by.id == Task.finished_by)
                .join(task_created_by, task_created_by.id == Task.created_by)
                .join(Task.created_bys)
                .filter(
                    and_(
                        Task.org_id == req_user.org_id,
                        or_(
                            and_(Task.finished_at >= start_period, Task.finished_at <= end_period),
                            Task.finished_at == None,  # noqa
                        ),
                    )
                )
                .all()
            )

        tasks = []

        for t, ta, tcb, tfb in tasks_qry:
            task_dict = t.fat_dict()
            task_dict["assignee"] = ta.as_dict() if ta is not None else None
            task_dict["created_by"] = tcb.as_dict()
            task_dict["finished_by"] = tfb.as_dict() if tfb is not None else None
            task_dict["status"] = t.task_statuses.as_dict()
            task_dict["type"] = t.task_types.as_dict()
            task_dict["priority"] = t.task_priorities.as_dict()
            tasks.append(task_dict)

        req_user.log(operation=Operations.GET, resource=Resources.TASKS)
        return self.ok({"tasks": tasks})


@tasks_route.route("/minimal")
class TasksMinimal(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASKS)
    @tasks_route.response(200, "Success", min_tasks_response)
    @tasks_route.response(403, "Insufficient privileges", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Get all tasks in an organisation with minimal info"""
        req_user = kwargs["req_user"]

        # start_period, end_period = self.validate_time_period(req.get_json())
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        with session_scope() as session:
            label1, label2, label3 = aliased(TaskLabel), aliased(TaskLabel), aliased(TaskLabel)
            tasks_qry = (
                session.query(
                    Task.id,
                    Task.description,
                    Task.priority,
                    Task.scheduled_for,
                    Task.status,
                    TaskType.label,
                    User.id,
                    User.first_name,
                    User.last_name,
                    label1,
                    label2,
                    label3,
                )
                .join(TaskType, TaskType.id == Task.type)
                .outerjoin(User, User.id == Task.assignee)
                .outerjoin(label1, label1.id == Task.label_1)
                .outerjoin(label2, label2.id == Task.label_2)
                .outerjoin(label3, label3.id == Task.label_3)
                .filter(
                    and_(
                        Task.org_id == req_user.org_id,
                        or_(
                            and_(Task.finished_at >= start_period, Task.finished_at <= end_period),
                            Task.finished_at == None,  # noqa
                        ),
                    )
                )
                .all()
            )

        tasks = []

        for task in tasks_qry:
            (
                id_,
                description,
                priority,
                scheduled_for,
                status,
                type_,
                assignee_id,
                assignee_fn,
                assignee_ln,
                label_1,
                label_2,
                label_3,
            ) = task

            # assignee is either null, or return their first and last name concat
            if assignee_fn is None and assignee_ln is None:
                assignee = None
            else:
                assignee = assignee_fn + " " + assignee_ln

            # convert labels to a list
            labels = [l.as_dict() for l in [label_1, label_2, label_3] if l is not None]

            # convert scheduled for to date
            if scheduled_for is not None:
                scheduled_for = scheduled_for.strftime(app.config["RESPONSE_DATE_FORMAT"])

            tasks.append(
                {
                    "id": id_,
                    "type": type_,
                    "description": description,
                    "priority": priority,
                    "status": status,
                    "assignee": assignee,
                    "assignee_id": assignee_id,
                    "labels": labels,
                    "scheduled_for": scheduled_for,
                }
            )
        return self.ok({"tasks": tasks})
