from flask_restx import fields

from app import api
from app.Models.Request.Common import NullableDateTime, NullableInteger


statuses = ["READY", "IN_PROGRESS", "COMPLETED"]

update_task_dtoupdate_task_request = api.model(
    "Update Task Request",
    {
        "id": fields.Integer(),
        "type_id": fields.Integer(required=True),
        "description": fields.String(),
        "status": fields.String(enum=statuses, required=True),
        "time_estimate": NullableInteger,
        "scheduled_for": NullableDateTime,
        "scheduled_notification_period": fields.Integer(),
        "assignee": fields.Integer(),
        "priority": fields.Integer(min=0, max=2, required=True),
        "labels": fields.List(fields.Integer, max_items=3),
    },
)

create_task_request = api.model(
    "Create Task Request",
    {
        "type_id": fields.Integer(),
        "description": fields.String(),
        "time_estimate": NullableInteger,
        "scheduled_for": NullableDateTime,
        "scheduled_notification_period": fields.Integer(),
        "assignee": fields.Integer(),
        "priority": fields.Integer(min=0, max=2),
        "labels": fields.List(fields.Integer(), max_items=3),
    },
)

assign_task_request = api.model("Assign Task Request", {"task_id": fields.Integer(), "assignee": fields.Integer()})

delay_task_request = api.model(
    "Delay Task Request", {"task_id": fields.Integer(), "delay_for": fields.Integer(), "reason": fields.String()}
)

transition_task_request = api.model(
    "Transition Task Request",
    {
        "task_id": fields.Integer(required=True),
        "task_status": fields.String(enum=statuses, required=True),
        "org_id": fields.Integer(),
    },
)

update_task_priority_request = api.model(
    "Update Task Priority Request",
    {"org_id": fields.Integer(), "task_id": fields.Integer(), "priority": fields.Integer(min=0, max=2)},
)
