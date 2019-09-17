from flask_restplus import fields

from app import api


escalation_policy_dto = api.model("Escalation Policy Response Model", {
    "display_order": fields.Integer(),
    "delay": fields.Integer(),
    "from_priority": fields.Integer(),
    "to_priority": fields.Integer(),
})

task_type_response_dto = api.model("Get Task Type Response Model", {
    "id": fields.Integer(),
    "label": fields.String(),
    "org_id": fields.Integer(),
    "disabled": fields.String(),
    "tooltip": fields.String(),
    "escalation_policies": fields.List(fields.Nested(escalation_policy_dto))
})

get_all_types_response_dto = api.model("Get all task types model", {
    "task_types": fields.List(fields.Nested(task_type_response_dto))
})
