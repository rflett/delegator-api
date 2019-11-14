from flask import Response, request
from flask_restplus import Namespace

from app import session_scope, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import Activity, Notification, Task
from app.Models.Enums import Operations, Resources, Events, TaskStatuses, ClickActions
from app.Models.Request import update_task_request, create_task_request
from app.Models.Response import message_response_dto, task_response
from app.Services import TaskService, UserService

task_route = Namespace(
    path="/task",
    name="Task",
    description="Manage a task"
)

task_service = TaskService()
user_service = UserService()


@task_route.route("/<int:task_id>")
class GetTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @task_route.response(200, "Success", task_response)
    @task_route.response(400, "Failed to get the task", message_response_dto)
    def get(self, task_id: int, **kwargs) -> Response:
        """Get a single task"""
        req_user = kwargs['req_user']

        task = task_service.get(task_id, req_user.org_id)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK,
            resource_id=task.id
        )
        return self.ok(task.fat_dict())


@task_route.route('/')
class ManageTask(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK)
    @task_route.expect(update_task_request)
    @task_route.response(200, "Success", task_response)
    @task_route.response(400, "Failed update the task", message_response_dto)
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
                task_service.unassign(
                    task=task_to_update,
                    req_user=req_user
                )
            else:
                task_service.assign(
                    task=task_to_update,
                    assignee=assignee,
                    req_user=req_user,
                    notify=False if task_to_update.status == TaskStatuses.SCHEDULED else True
                )

        # transition
        task_status = task_attrs.pop('status')
        if task_to_update.status != task_status:
            task_service.transition(
                task=task_to_update,
                status=task_status,
                req_user=req_user
            )

        # change priority
        task_priority = task_attrs.pop('priority')
        if task_to_update.priority != task_priority:
            task_service.change_priority(
                task=task_to_update,
                priority=task_priority
            )

        # don't update scheduled info if it wasn't scheduled to begin with, or the notification has been sent
        if task_to_update.scheduled_for is None \
                and task_to_update.scheduled_notification_period is None \
                or task_to_update.scheduled_notification_sent:
            task_attrs.pop('scheduled_for')
            task_attrs.pop('scheduled_notification_period')

        # update the labels
        labels = self._get_labels(task_attrs.pop('labels'))

        attrs_to_update = {
            **task_attrs,
            **labels
        }

        # for each value left in the task attrs, if the task has that attribute, update it
        # previous attributes such as priority and status have been popped from the request dict so will not be updated
        # again here
        with session_scope():
            for k, v in attrs_to_update.items():
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
    @task_route.expect(create_task_request)
    @task_route.response(201, "Created", task_response)
    @task_route.response(400, "Failed to create the task", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Creates a task"""
        req_user = kwargs['req_user']

        task_attrs = self.validate_create_task_request(request.get_json(), **kwargs)

        if task_attrs['scheduled_for'] is not None and task_attrs['scheduled_notification_period'] is not None:
            return self.created(self._schedule_task(task_attrs, req_user))
        else:
            return self.created(self._create_task(task_attrs, req_user))

    def _create_task(self, task_attrs: dict, req_user) -> dict:
        """Creates a new task"""
        with session_scope() as session:
            task = Task(
                org_id=req_user.org_id,
                type=task_attrs['type'],
                description=task_attrs['description'],
                status=TaskStatuses.READY,
                time_estimate=task_attrs['time_estimate'],
                priority=task_attrs['priority'],
                created_by=req_user.id,
                **self._get_labels(task_attrs.pop('labels'))
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
            task_service.assign(
                task=task,
                assignee=task_attrs.get('assignee'),
                req_user=req_user
            )
        else:
            created_notification = Notification(
                title="Task created",
                event_name=Events.task_created,
                msg=f"{task.label()} task has been created.",
                click_action=ClickActions.ASSIGN_TO_ME,
                task_action_id=task.id,
                user_ids=user_service.get_all_user_ids(req_user.org_id)
            )
            created_notification.push()

        return task.fat_dict()

    def _schedule_task(self, task_attrs: dict, req_user) -> dict:
        """Schedules a new task"""
        with session_scope() as session:
            task = Task(
                org_id=req_user.org_id,
                type=task_attrs['type'],
                description=task_attrs['description'],
                status=TaskStatuses.SCHEDULED,
                scheduled_for=task_attrs['scheduled_for'],
                scheduled_notification_period=task_attrs['scheduled_notification_period'],
                time_estimate=task_attrs['time_estimate'],
                priority=task_attrs['priority'],
                created_by=req_user.id,
                **self._get_labels(task_attrs.pop('labels'))
            )
            session.add(task)

        Activity(
            org_id=task.org_id,
            event=Events.task_scheduled,
            event_id=task.id,
            event_friendly=f"Scheduled by {req_user.name()}."
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_scheduled_task,
            event_id=req_user.id,
            event_friendly=f"Scheduled task {task.label()}."
        ).publish()
        req_user.log(
            operation=Operations.CREATE,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"Scheduled task {task.as_dict()}")

        # optionally assign the task if an assignee was present in the create task request
        if task_attrs.get('assignee') is not None:
            task_service.assign(
                task=task,
                assignee=task_attrs.get('assignee'),
                req_user=req_user,
                notify=False
            )

        return task.fat_dict()

    @staticmethod
    def _get_labels(label_attrs: dict) -> dict:
        """labels provided as a list, so map their index to the Task column"""
        labels = {
            "label_1": None,
            "label_2": None,
            "label_3": None
        }
        for i in range(1, len(label_attrs) + 1):
            labels[f'label_{i}'] = label_attrs[i - 1]
        return labels
