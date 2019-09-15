from flask_restplus import fields

from app import api

# TODO these will eventually be defined in their own models and should be imported here
role_dto = api.model("Role", {
    "id": fields.String,
    "rank": fields.Integer,
    "name": fields.String,
    "description": fields.String
})

settings_dto = api.model("Settings", {
    "user_id": fields.Integer,
    "tz_offset": fields.String
})

login_response_dto = api.model("Login Response", {
    "id": fields.Integer,
    "org_id": fields.Integer,
    "email": fields.String,
    "first_name": fields.String,
    "last_name": fields.String,
    "role": fields.Nested(role_dto),
    "role_before_locked": fields.Boolean,
    "disabled": fields.String,
    "job_title": fields.String,
    "deleted": fields.String,
    "created_at": fields.String,
    "created_by": fields.String,
    "updated_at": fields.String,
    "updated_by": fields.String,
    "settings": fields.Nested(settings_dto),
    "jwt": fields.String
})
