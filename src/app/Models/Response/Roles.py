from flask_restplus import fields

from app import api

response_roles = ['ORG_ADMIN', 'MANAGER', 'STAFF', 'USER', 'LOCKED']

role_dto = api.model("Role", {
    "id": fields.Integer(),
    "rank": fields.Integer(min=0, max=2),
    "name": fields.String(enum=response_roles),
    "description": fields.String()
})

roles_response = api.model("Roles Response", {
    'roles': fields.List(fields.Nested(role_dto))
})
