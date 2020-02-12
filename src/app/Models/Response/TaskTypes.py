from flask_restx import fields

from app import api
from app.Models.Response.Common import NullableDateTime


escalation_policy_dto = api.model(
    "Escalation Policy Response",
    {
        "task_type_id": fields.Integer,
        "display_order": fields.Integer(min=1, max=2),
        "delay": fields.Integer(),
        "from_priority": fields.Integer(min=0, max=1),
        "to_priority": fields.Integer(min=1, max=2),
    },
)

task_type_response = api.model(
    "Task Type Response",
    {
        "id": fields.Integer(),
        "label": fields.String(),
        "default_time_estimate": fields.Integer(min=0),
        "default_description": fields.String(),
        "default_priority": fields.Integer(enum=[1, 2, 3]),
        "org_id": fields.Integer(),
        "disabled": NullableDateTime,
        "tooltip": fields.String(),
        "escalation_policies": fields.List(fields.Nested(escalation_policy_dto)),
    },
)

task_types_response = api.model("Task Types Response", {"task_types": fields.List(fields.Nested(task_type_response))})
