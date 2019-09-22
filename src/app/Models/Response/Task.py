from flask_restplus import fields

from app import api
from app.Models.Response.Common import NullableDateTime
from app.Models.Response.TaskTypes import task_type_response
from app.Models.Response.User import user_response

response_statuses = ['READY', 'IN_PROGRESS', 'DELAYED', 'COMPLETED', 'CANCELLED']

task_status_dto = api.model("Task Status", {
    "status":  fields.String(enum=response_statuses),
    "label": fields.String(),
    "disabled": fields.Boolean(),
    "tooltip": fields.String()
})

task_priority_dto = api.model("Task Priority", {
    "priority":  fields.Integer(min=0, max=1),
    "label": fields.String(),
})

task_statuses_response = api.model("Task Statuses Response", {
    'statuses': fields.List(fields.Nested(task_status_dto))
})

task_priorities_response = api.model("Task Priorities Response", {
    'priorities': fields.List(fields.Nested(task_priority_dto))
})

task_response = api.model("Task Response", {
    "id": fields.Integer(),
    "org_id": fields.Integer(),
    "type": fields.Nested(task_type_response),
    "description": fields.String(),
    "status": fields.Nested(task_status_dto),
    "time_estimate": fields.String(),
    "due_time": NullableDateTime,
    "assignee": fields.Nested(user_response),
    "priority": fields.Nested(task_priority_dto),
    "created_by": fields.Nested(user_response),
    "created_at": fields.DateTime(),
    "started_at": NullableDateTime,
    "finished_by": fields.Nested(user_response),
    "finished_at": NullableDateTime,
    "status_changed_at": NullableDateTime,
    "priority_changed_at": NullableDateTime,
})

tasks_response = api.model("Tasks Response", {
    'tasks': fields.List(fields.Nested(task_response))
})

delayed_task_response = api.model("Delayed Tasks Response", {
    "task_id": fields.Integer(),
    "delay_for": fields.Integer(),
    "delayed_at": fields.DateTime(),
    "delayed_by": fields.Nested(user_response),
    "reason": fields.String(),
    "snoozed": NullableDateTime,
    "expired": NullableDateTime
})
