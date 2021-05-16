import json
from os import getenv

import boto3
import structlog
from flask import current_app

from app.Models.Dao import User
from app.Models.Enums import EmailTemplates

sqs = boto3.resource("sqs")
log = structlog.getLogger()


class Email(object):
    def __init__(self, recipient: str):
        self.recipient = recipient
        self.web_url = current_app.config["WEBSITE_URL"]

    def send_welcome(self, first_name: str):
        dto = {
            "recipient": self.recipient,
            "template": EmailTemplates.WELCOME,
            "template_data": {
                "first_name": first_name,
                "website_url": self.web_url,
                "website_link": f"https://{self.web_url}",
                "faq_link": f"https://{self.web_url}/faq/",
                "kb_link": f"https://{self.web_url}/kb/",
                "login_link": f"app.{self.web_url}/login",
                "privacy_link": f"https://{self.web_url}/privacy-policy/",
            },
        }
        """Sends a welcome email"""
        log.info(f"Sending welcome email to {self.recipient}")
        self._publish(dto)

    def send_password_reset(self, first_name: str, link: str):
        """Sends a password reset email"""
        dto = {
            "recipient": self.recipient,
            "template": EmailTemplates.RESET_PASSWORD,
            "template_data": {
                "first_name": first_name,
                "c2a_link": link,
                "privacy_link": f"https://{self.web_url}/privacy-policy/",
                "website_url": self.web_url,
                "website_link": f"https://{self.web_url}",
            },
        }
        log.info(f"Sending password reset email to {self.recipient}")
        self._publish(dto)

    def send_welcome_new_user(self, first_name: str, link: str, inviter: User):
        """Sends a welcome email to a new user"""
        dto = {
            "recipient": self.recipient,
            "template": EmailTemplates.WELCOME_NEW_USER,
            "template_data": {
                "first_name": first_name,
                "c2a_link": link,
                "inviter_name": inviter.first_name,
                "org_name": inviter.orgs.name,
                "kb_link": f"https://{self.web_url}/kb/",
                "privacy_link": f"https://{self.web_url}/privacy-policy/",
                "website_url": self.web_url,
                "website_link": f"https://{self.web_url}",
            },
        }
        log.info(f"Sending welcome email to {self.recipient} from {inviter.email}")
        self._publish(dto)

    def send_contact_us(self, first_name: str, last_name: str, email: str, lead: str, question: str):
        """Sends a contact us email to Delegator"""
        dto = {
            "recipient": self.recipient,
            "template": EmailTemplates.CONTACT_US,
            "template_data": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "lead": lead,
                "question": question,
            },
        }
        log.info(f"Sending contact-us from {email}")
        self._publish(dto)

    @staticmethod
    def _publish(dto: dict) -> None:
        """Publishes an email to SNS"""
        if getenv("MOCK_AWS"):
            log.info(f"WOULD have sent email message {dto}")
            return None

        email_queue = sqs.Queue(current_app.config["EMAIL_SQS_ENDPOINT"])

        try:
            email_queue.send_message(MessageBody=json.dumps(dto))
        except Exception as e:
            log.error(e)
