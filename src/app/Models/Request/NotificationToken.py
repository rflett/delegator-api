from flask_restplus import fields

from app import api

register_notification_token_dto = api.model("Register Notification Token Model", {
    "token": fields.String,
    "token_type": fields.String
})

deregister_notification_token_dto = api.model("Deregister Notification Token Model", {
    "token_type": fields.String
})
