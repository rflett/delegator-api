from flask_restplus import fields
from app import api

silence_notifications_dto = api.model("Silence Notifications Dto", {
    "silence_until": fields.DateTime(d_format='2019-09-17T19:08:00+10:00'),
    "silenced_option": fields.Integer()
})
