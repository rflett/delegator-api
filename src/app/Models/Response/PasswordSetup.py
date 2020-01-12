from flask_restplus import fields

from app import api


password_setup_response = api.model("New Password Setup Response", {"email": fields.String()})
