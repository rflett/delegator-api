from flask_restplus import fields

from app import api

message_response_dto = api.model("Message Response", {
    "msg": fields.String
})
