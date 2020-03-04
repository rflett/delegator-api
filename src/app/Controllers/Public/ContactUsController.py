from flask import current_app
from flask_restx import Namespace, Resource, reqparse
import requests

from app.Extensions.Database import session_scope
from app.Models.Dao import ContactUsEntry
from app.Models import Email

api = Namespace(path="/contact", name="Contact Us", description="Sends an email to the Delegator team")

parser = reqparse.RequestParser()
parser.add_argument("first_name", type=str, location="form", required=True, help="Your first name")
parser.add_argument("last_name", type=str, location="form", help="Your surname")
parser.add_argument("email", type=str, location="form", required=True, help="Your email")
parser.add_argument("lead", type=str, location="form", help="Where did you find us?")
parser.add_argument("question", type=str, location="form", required=True, help="What is your question?")
parser.add_argument("g-recaptcha-response", type=str, location="form", required=True, help="Recaptcha code")


@api.route("/")
class Version(Resource):
    @api.response(204, "Success")
    @api.expect(parser)
    def post(self):
        """Sends an email to the Delegator team"""

        # parse the request form-data
        args = parser.parse_args()

        # verify captcha
        try:
            r = requests.post(
                url="https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": current_app.config["CONTACT_US_GOOGLE_RECAPTCHA_SECRET"],
                    "response": args.pop("g-recaptcha-response")
                },
                timeout=5
            )
            response_body = r.json()

            if not response_body["success"]:
                current_app.logger.error(f"failed to verify recaptcha - {response_body['error-codes']}")
            else:
                current_app.logger.info("successfully verified recaptcha")

        except requests.RequestException:
            current_app.logger.error("failed to make request for verifying recaptcha")

        # add to db
        with session_scope() as session:
            entry = ContactUsEntry(**args)
            session.add(entry)

        # send email
        email = Email("devops@delegator.com.au")
        email.send_contact_us(**entry.to_email())

        return "", 204
