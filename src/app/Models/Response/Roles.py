from flask_restplus import fields

from app import api

response_roles = ['ORG_ADMIN', 'MANAGER', 'STAFF', 'USER', 'LOCKED']

role_response = api.model("Role Response", {
    "id": fields.Integer(),
    "rank": fields.Integer(min=0, max=2),
    "name": fields.String(enum=response_roles),
    "description": fields.String()
})
