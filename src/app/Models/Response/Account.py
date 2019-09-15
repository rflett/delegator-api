from flask_restplus import fields

from app import api

login_response_dto = api.models("Login Response", {
    "deleted": fields.DateTime,
    "disabled": fields.DateTime,
    "email": fields.String,
    "first_name": fields.String,
    "last_name": fields.String,
    "id": 1,
    "job_title": fields.String,
    "org_id": 1,
    "org_name": fields.String,
    "role": fields.String,
    "role_description": fields.String,
    "role_name": fields.String,
    "jwt": fields.String
})
