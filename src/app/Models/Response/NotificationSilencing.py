from flask_restplus import fields

from app import api

get_silenced_option_dto = api.model("Get Silenced Option Dto", {
    "option": fields.Integer
})
