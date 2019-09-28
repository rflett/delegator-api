from flask_restplus import fields

from app import api
from app.Models.Request.Common import NullableDateTime

roles = ["ORG_ADMIN", "MANAGER", "STAFF", "USER"]

create_user_request = api.model("Create User Request", {
    "email": fields.String(required=True),
    "role_id": fields.String(enum=roles, required=True),
    "first_name": fields.String(required=True),
    "last_name": fields.String(required=True),
    "job_title": fields.String(required=False),
    "disabled": NullableDateTime(required=False)
})

update_user_request = api.model("Update User Request", {
    "id": fields.String(required=True),
    "role_id": fields.String(enum=roles, required=True),
    "first_name": fields.String(required=False),
    "last_name": fields.String(required=False),
    "job_title": fields.String(required=False),
    "disabled": NullableDateTime(required=False)
})
