from flask_restplus import fields

from app import api


escalation_policy_dto = api.model("Escalation Policy Request", {
    "display_order": fields.Integer(min=1, max=2),
    "delay": fields.Integer(),
    "from_priority": fields.Integer(min=0, max=1),
    "to_priority": fields.Integer(min=1, max=2),
})

create_task_type_request = api.model("Create Task Type Request", {
    'label': fields.String(required=True),
    'default_time_estimate': fields.Integer(min=0),
    'default_description': fields.String(),
    'default_priority': fields.Integer(enum=[1, 2, 3])
})

update_task_type_request = api.model("Update Task Type Request", {
    "id": fields.Integer(),
    "label": fields.String(),
    'default_time_estimate': fields.Integer(min=0),
    'default_description': fields.String(),
    'default_priority': fields.Integer(enum=[1, 2, 3]),
    "escalation_policies": fields.List(fields.Nested(escalation_policy_dto))
})

disable_task_type_request = api.model("Disable Task Type Request", {
    "id": fields.Integer()
})