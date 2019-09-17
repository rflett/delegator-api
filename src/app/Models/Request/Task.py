from flask_restplus import fields

from app import api
from app.Models.Request.Common import NullableDateTime, NullableInteger


statuses = ['READY', 'IN_PROGRESS', 'COMPLETED']

update_task_request = api.model("Update Task Request", {
    'id': fields.Integer(),
    'type_id': fields.Integer(),
    'description': fields.String(),
    'status': fields.String(enum=statuses),
    'time_estimate': NullableInteger,
    'due_time': NullableDateTime,
    'assignee': fields.Integer(),
    'priority': fields.Integer(min=0, max=2),
})

create_task_request = api.model("Create Task Request", {
    'type_id': fields.Integer(),
    'description': fields.String(),
    'status': fields.String(enum=statuses),
    'time_estimate': NullableInteger,
    'due_time': NullableDateTime,
    'assignee': fields.Integer(),
    'priority': fields.Integer(min=0, max=2),
})

assign_task_request = api.model("Assign Task Request", {
    "task_id": fields.Integer(),
    "assignee": fields.Integer()
})

delay_task_request = api.model("Delay Task Request", {
    "task_id": fields.Integer(),
    "delay_for": fields.Integer(),
    "reason": fields.String()
})

get_delayed_task_request = api.model("Get Delayed Task Request", {
    "task_id": fields.Integer()
})

transition_task_request = api.model("Transition Task Request", {
    "task_id": fields.Integer(),
    "task_status": fields.String(enum=statuses)
})


get_available_transitions_request = api.model("Get Available Transitions Request", {
    "task_id": fields.Integer()
})

update_task_priority_request = api.model("Update Task Priority Request", {
    "org_id": fields.Integer(),
    "task_id": fields.Integer(),
    "priority": fields.Integer(min=0, max=2)
})
