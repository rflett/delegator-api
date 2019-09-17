from flask_restplus import fields

from app import api

role_dto = api.model("Status", {
    "id": fields.Integer(),
    "rank": fields.String(),
    "name": fields.String(),
    "description": fields.String()
})
