from flask_restplus import fields

from app import api

register_notification_token_request = api.model("Register Notification Token Request", {
    "token": fields.String,
    "token_type": fields.String
})

deregister_notification_token_request = api.model("Deregister Notification Token Request", {
    "token_type": fields.String
})
