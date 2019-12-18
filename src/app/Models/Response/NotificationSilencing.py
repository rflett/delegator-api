from flask_restplus import fields

from app import api
from app.Models.Response.Common import NullableDateTime

get_silenced_info_dto = api.model("Get Silenced Info Dto", {
    "silenced_option": fields.Integer(min=0, max=8),
    "silence_until": NullableDateTime()
})
