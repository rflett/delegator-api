from flask_restplus import fields

from app import api

# TODO use this for nullable date times
# class NullableString(fields.String):
#     __schema_type__ = ['string', 'null']
#     __schema_example__ = 'nullable string'

task_type_dto = api.model("Task Type", {
    "id": fields.Integer(),
    "label": fields.String(),
    "org_id": fields.Integer(),
    "disabled": fields.DateTime(),
    "tooltip": fields.String()
})

task_status_dto = api.model("Task Status", {
    "status":  fields.String(),
    "label": fields.String(),
    "disabled": fields.Boolean(),
    "tooltip": fields.String()
})

task_priority_dto = api.model("Task Priority", {
    "priority":  fields.Integer(),
    "label": fields.String(),
})

get_task_statuses_response_dto = api.model("Task Statuses Model", {
    'statuses': fields.List(fields.Nested(task_status_dto))
})

get_task_priorities_response_dto = api.model("Task Priorities Model", {
    'priorities': fields.List(fields.Nested(task_priority_dto))
})

task_response_dto = api.model("Task Model", {
    "id": fields.Integer(),
    "org_id": fields.Integer(),
    "type": fields.Nested(task_type_dto),
    "description": fields.String(),
    "status": fields.Nested(task_status_dto),
    "time_estimate": fields.String(),
    "due_time": fields.DateTime(),
    "assignee": fields.Integer(),  # TODO import a User model
    "priority": fields.Nested(task_priority_dto),
    "created_by": fields.Integer(),  # TODO import a User model
    "created_at": fields.DateTime(),
    "started_at": fields.DateTime(),
    "finished_by": fields.Integer(),  # TODO import a User model
    "finished_at": fields.DateTime(),
    "status_changed_at": fields.DateTime(),
    "priority_changed_at": fields.DateTime(),
})

get_tasks_response_dto = api.model("Tasks Model", {
    'tasks': fields.List(fields.Nested(task_response_dto))
})
