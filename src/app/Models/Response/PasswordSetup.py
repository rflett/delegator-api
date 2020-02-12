from flask_restx import fields

from app import api


password_setup_response = api.model("New Password Config Response", {"email": fields.String()})
