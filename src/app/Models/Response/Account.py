from flask_restx import fields

from app import api
from app.Models.Response.Roles import roles_response
from app.Models.Response.Common import NullableDateTime, NullableString


# TODO import from user settings
user_settings_response = api.model("User Settings Response", {"user_id": fields.Integer, "tz_offset": fields.String})

login_response = api.model(
    "Login Response",
    {
        "id": fields.Integer,
        "org_id": fields.Integer,
        "email": fields.String,
        "first_name": fields.String,
        "last_name": fields.String,
        "role": fields.Nested(roles_response),
        "role_before_locked": NullableString,
        "disabled": NullableDateTime,
        "job_title": fields.String,
        "deleted": NullableDateTime,
        "created_at": fields.String,
        "created_by": fields.String,
        "updated_at": NullableDateTime,
        "updated_by": NullableString,
        "settings": fields.Nested(user_settings_response),
        "jwt": fields.String,
    },
)

signup_response = api.model("Signup Response", {"url": fields.String})
