from flask_restplus import fields

from app import api
from app.Models.Response import roles_response
from app.Models.Response.Account import user_settings_response
from app.Models.Response.Common import NullableString, NullableDateTime

user_response = api.model("Login Response", {
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

user_activity_response = api.model("User activity response", {
    "activity": fields.String,
    "activity_timestamp": fields.DateTime,
    "event_friendly": fields.String
})

created_user_response = api.model("User created response", {
    "id": fields.Integer,
    "email": fields.String,
    "first_name": fields.String,
    "last_name": fields.String,
    "role_name": fields.String,
    "job_title": fields.String
})

user_list_response = api.model("User Information", {
    "deleted": fields.DateTime,
    "disabled": fields.DateTime,
    "email": fields.String,
    "first_name": fields.String,
    "id": fields.Integer,
    "job_title": fields.String,
    "last_name": fields.String,
    "org_id": fields.Integer,
    "org_name": fields.String,
    "role": fields.String,
    "role_description": fields.String,
    "role_name": fields.String
})
