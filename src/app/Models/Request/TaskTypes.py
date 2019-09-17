from flask_restplus import fields

from app import api


escalation_policy_dto = api.model("Escalation Policy Model", {
    "display_order": fields.Integer(),
    "delay": fields.Integer(),
    "from_priority": fields.Integer(),
    "to_priority": fields.Integer(),
})

create_task_type_request_dto = api.model("Create Task Type Model", {
    'label': fields.String()
})

update_task_type_request_dto = api.model("Update Task Type Model", {
    "id": fields.Integer(),
    "label": fields.String(),
    "escalation_policies": fields.List(fields.Nested(escalation_policy_dto))
})

disable_task_type_request_dto = api.model("Disable Task Type Model", {
    "id": fields.Integer()
})
