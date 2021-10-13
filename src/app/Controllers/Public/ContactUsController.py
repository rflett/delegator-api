import requests
import structlog
from flask import current_app, request
from flask_restx import fields, Namespace

from app.Controllers.Base import RequestValidationController
from app.Extensions.Database import session_scope
from app.Models import Email
from app.Models.Dao import ContactUsEntry

api = Namespace(path="/contact", name="Contact Us", description="Sends an email to the Delegator team")
log = structlog.getLogger()


@api.route("/")
class ContactUs(RequestValidationController):
    contact_request = api.model(
        "Contact Request",
        {
            "first_name": fields.String(required=True),
            "last_name": fields.String(),
            "email": fields.String(required=True),
            "lead": fields.String(),
            "question": fields.String(required=True),
            "g-recaptcha-response": fields.String(required=True),
        },
    )

    @api.expect(contact_request, validate=True)
    @api.response(204, "Success")
    def post(self):
        """Sends an email to the Delegator team"""
        request_body = request.get_json()

        # validate the form data
        self.validate_email(request_body["email"])

        captcha_code = request_body["g-recaptcha-response"]

        # verify captcha
        try:
            r = requests.post(
                url="https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": current_app.config["CONTACT_US_GOOGLE_RECAPTCHA_SECRET"],
                    "response": captcha_code,
                },
                timeout=5,
            )
            response_body = r.json()

            if not response_body["success"]:
                log.error(f"failed to verify recaptcha - {response_body['error-codes']}")
                return "", 204
            else:
                log.info("successfully verified recaptcha")

        except requests.RequestException:
            log.error("failed to make request for verifying recaptcha")
            return "", 204

        # add to db
        with session_scope() as session:
            entry = ContactUsEntry(
                first_name=request_body["first_name"],
                last_name=request_body["last_name"],
                email=request_body["email"],
                lead=request_body["lead"],
                question=request_body["question"]
            )
            session.add(entry)

        # send email
        email = Email("contact@delegator.com.au")
        email.send_contact_us(**entry.to_email())

        return "", 204
