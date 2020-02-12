from flask_restx import fields

from app import api
from app.Models.Response import role_dto
from app.Models.Response.Account import user_settings_response
from app.Models.Response.Common import NullableString, NullableDateTime


user_response = api.model(
    "User Response",
    {
        "id": fields.Integer,
        "org_id": fields.Integer,
        "email": fields.String,
        "first_name": fields.String,
        "last_name": fields.String,
        "role": fields.Nested(role_dto),
        "role_before_locked": NullableString,
        "disabled": NullableDateTime,
        "job_title": fields.String,
        "deleted": NullableDateTime,
        "created_at": fields.String,
        "created_by": fields.String,
        "updated_at": NullableDateTime,
        "updated_by": NullableString,
        "invite_accepted": fields.Boolean,
        "settings": fields.Nested(user_settings_response),
    },
)

min_user_response = api.model(
    "Minimal User Response",
    {
        "id": fields.Integer,
        "email": fields.String,
        "first_name": fields.String,
        "last_name": fields.String,
        "job_title": fields.String,
    },
)

get_users_response = api.model("Get Users Response", {"users": fields.List(fields.Nested(user_response))})
get_min_users_response = api.model(
    "Get Minimal Users Response", {"users": fields.List(fields.Nested(min_user_response))}
)
