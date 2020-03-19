import json
from os import getenv

from flask import current_app
import boto3

from app.Models.Dao import User
from app.Models.Enums import EmailTemplates

sns = boto3.resource("sns")


class Email(object):
    def __init__(self, recipient: str):
        self.recipient = recipient

    def send_welcome(self, first_name: str):
        """Sends a welcome email"""
        dto = {
            "recipient": self.recipient,
            "template": EmailTemplates.WELCOME,
            "template_data": {"first_name": first_name},
        }
        current_app.logger.info(f"Sending welcome email to {self.recipient}")
        self._publish(dto)

    def send_password_reset(self, first_name: str, link: str):
        """Sends a password reset email"""
        dto = {
            "recipient": self.recipient,
            "template": EmailTemplates.RESET_PASSWORD,
            "template_data": {"first_name": first_name, "c2a_link": link},
        }
        current_app.logger.info(f"Sending password reset email to {self.recipient}")
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
            },
        }
        current_app.logger.info(f"Sending welcome email to {self.recipient} from {inviter.email}")
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
        current_app.logger.info(f"Sending contact-us from {email}")
        self._publish(dto)

    @staticmethod
    def _publish(dto: dict) -> None:
        """ Publishes an email to SNS """
        if getenv("MOCK_AWS"):
            current_app.logger.info(f"WOULD have sent email message {dto}")
            return None

        email_sns_topic = sns.Topic(current_app.config["EMAIL_SNS_TOPIC_ARN"])

        try:
            email_sns_topic.publish(
                TopicArn=email_sns_topic.arn, Message=json.dumps({"default": json.dumps(dto)}), MessageStructure="json"
            )
        except Exception as e:
            current_app.logger.error(e)
