from flask_restplus import fields

from app import api

status_dto = api.models("Status", {
    "id": fields.Integer,
    "rank": fields.String,
    "name": fields.String,
    "description": fields.String
})
