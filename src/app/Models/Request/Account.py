from flask_restplus import fields

from app import api

login_request = api.model("Login Request", {
    "email": fields.String,
    "password": fields.String
})
