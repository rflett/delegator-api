from flask_restplus import fields

from app import api

# TODO use this for nullable date times
# class NullableString(fields.String):
#     __schema_type__ = ['string', 'null']
#     __schema_example__ = 'nullable string'

update_task_dto = api.model("Update Task Model", {
    'id': fields.Integer(),
    'type_id': fields.Integer(),
    'description': fields.String(),
    'status': fields.String(),
    'time_estimate': fields.Integer(),
    'due_time': fields.DateTime(),
    'assignee': fields.Integer(),
    'priority': fields.Integer(),
})

create_task_dto = api.model("Create Task Model", {
    'type_id': fields.Integer(),
    'description': fields.String(),
    'status': fields.String(),
    'time_estimate': fields.Integer(),
    'due_time': fields.DateTime(),
    'assignee': fields.Integer(),
    'priority': fields.Integer(),
})

assign_task_dto = api.model("Assign Task Model", {
    "task_id": fields.Integer(),
    "assignee": fields.Integer()
})

delay_task_dto = api.model("Delay Task Model", {
    "task_id": fields.Integer(),
    "delay_for": fields.Integer(),
    "reason": fields.String()
})

get_delayed_task_dto = api.model("Get Delayed Task Model", {
    "task_id": fields.Integer()
})

transition_task_dto = api.model("Transition Task Model", {
    "task_id": fields.Integer(),
    "task_status": fields.String()
})


get_available_transitions_dto = api.model("Get Available Transitions Task Model", {
    "task_id": fields.Integer()
})

update_task_priority_dto = api.model("Update Task Priority Model", {
    "org_id": fields.Integer(),
    "task_id": fields.Integer(),
    "priority": fields.Integer(),
})
