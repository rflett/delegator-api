from flask_restplus import fields

from app import api
from app.Models.Response import roles_response
from app.Models.Response.Account import user_settings_response
from app.Models.Response.Common import NullableString, NullableDateTime

login_response = api.model("Login Response", {
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
    "jwt": fields.String
})

user_response = api.model("User Response", {
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
    "settings": fields.Nested(user_settings_response)
})

get_users_response = api.model("Get Users Response", {
    "users": fields.List(fields.Nested(user_response))
})
