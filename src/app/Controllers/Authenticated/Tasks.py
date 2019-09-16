import datetime
from dateutil import tz

from flask import request, Response
from flask_restplus import Namespace
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from app import session_scope, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import User, Task, Activity, TaskPriority, TaskStatus, Notification
from app.Models.Enums import Events, Operations, Resources
from app.Models.Request import update_task_dto, create_task_dto
from app.Models.Response import task_response_dto, message_response_dto, get_task_statuses_response_dto, \
    get_task_priorities_response_dto, get_tasks_response_dto
from app.Services import UserService

tasks_route = Namespace(
    path="/tasks",
    name="Tasks",
    description="Manage tasks"
)

user_service = UserService()


@tasks_route.route("/")
class Tasks(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASKS)
    @tasks_route.response(200, "Success", get_tasks_response_dto)
    def get(self, **kwargs) -> Response:
        """Get all tasks in an organisation"""
        req_user = kwargs['req_user']

        # start_period, end_period = self.validate_time_period(req.get_json())
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        # join across all related tables to get full info
        with session_scope() as session:
            task_assignee, task_created_by, task_finished_by = aliased(User), aliased(User), aliased(User)
            tasks_qry = session \
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
        return self.ok(tasks)

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK)
    @tasks_route.expect(update_task_dto)
    @tasks_route.response(200, "Success", task_response_dto)
    @tasks_route.response(400, "Failed to update the organisation", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Update a task """
        req_user = kwargs['req_user']

        task_attrs = self.validate_update_task_request(request.get_json(), **kwargs)

        # update the task
        task_to_update = task_attrs['task']

        # if the assignee isn't the same as before then assign someone to it, if the new assignee is null or
        # omitted from the request, then assign the task
        assignee = task_attrs.pop('assignee', None)
        if task_to_update.assignee != assignee:
            if assignee is None:
                self._unassign_task(
                    task=task_to_update,
                    req_user=req_user
                )
            else:
                self._assign_task(
                    task=task_to_update,
                    assignee=assignee,
                    req_user=req_user
                )

        # transition
        task_status = task_attrs.pop('status')
        if task_to_update.status != task_status:
            self._transition_task(
                task=task_to_update,
                status=task_status,
                req_user=req_user
            )

        # change priority
        task_priority = task_attrs.pop('priority')
        if task_to_update.priority != task_priority:
            self._change_task_priority(
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
        return self.ok(task_to_update.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK)
    @tasks_route.expect(create_task_dto)
    @tasks_route.response(200, "Success", task_response_dto)
    @tasks_route.response(400, "Failed to update the organisation", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Creates a task"""
        req_user = kwargs['req_user']

        task_attrs = self.validate_create_task_request(request.get_json(), **kwargs)

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
            self._assign_task(
                task=task,
                assignee=task_attrs.get('assignee'),
                req_user=req_user
            )
        else:
            Notification(
                msg=f"{task.label()} task has been created.",
                user_ids=self._all_user_ids(req_user.org_id)
            ).push()

        return self.created(task.fat_dict())


@tasks_route.route('/statuses')
class TaskStatuses(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_STATUSES)
    @tasks_route.response(200, "Success", get_task_statuses_response_dto)
    @tasks_route.response(400, "Failed to update the organisation", message_response_dto)
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


@tasks_route.route('/priorities')
class TaskPriorities(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_PRIORITIES)
    @tasks_route.response(200, "Success", get_task_priorities_response_dto)
    @tasks_route.response(400, "Failed to update the organisation", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns all task priorities """
        req_user = kwargs['req_user']

        with session_scope() as session:
            task_pr_qry = session.query(TaskPriority).all()

        task_priorities = [tp.as_dict() for tp in task_pr_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_PRIORITIES
        )
        return self.ok(task_priorities)
