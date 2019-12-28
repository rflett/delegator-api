from flask_restplus import fields

from app import api

login_request = api.model("Login Request", {
    "email": fields.String,
    "password": fields.String
})

signup_request = api.model("Signup Request", {
    "org_name": fields.String,
    "email": fields.String,
    "password": fields.String,
    "first_name": fields.String,
    "last_name": fields.String,
    "job_title": fields.String,
    "plan_id": fields.String,
})

password_setup_request = api.model("Password setup request", {
    "password": fields.String(required=True),
    "invite_link": fields.String(required=True)
})
