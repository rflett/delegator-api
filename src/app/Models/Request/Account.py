from flask_restplus import fields

from app import api

login_dto = api.model("Login Model", {
    "email": fields.String,
    "password": fields.String
})
