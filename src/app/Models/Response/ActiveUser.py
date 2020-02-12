from flask_restx import fields

from app import api

active_user_dto = api.model(
    "ActiveUser",
    {
        "user_id": fields.Integer(),
        "org_id": fields.Integer(),
        "first_name": fields.String(),
        "last_name": fields.String(),
        "last_active": fields.String(),
    },
)

active_user_response_dto = api.model("ActiveUsers", {"active_users": fields.List(fields.Nested(active_user_dto))})
