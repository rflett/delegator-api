import json
from os import getenv

from app import email_sns_topic, logger
from app.Models import User
from app.Models.Enums import EmailTemplates


class Email(object):

    def __init__(self, recipient: User):
        self.recipient = recipient

    def send_welcome(self):
        """Sends a welcome email"""
        dto = {
            "recipient": self.recipient.email,
            "template": EmailTemplates.WELCOME,
            "template_data": {
                "first_name": self.recipient.first_name
            }
        }
        logger.info(f"Sending welcome email to {self.recipient.email}")
        self._publish(dto)

    def send_password_reset(self, link: str):
        """Sends a password reset email"""
        dto = {
            "recipient": self.recipient.email,
            "template": EmailTemplates.RESET_PASSWORD,
            "template_data": {
                "first_name": self.recipient.first_name,
                "c2a_link": link
            }
        }
        logger.info(f"Sending password reset email to {self.recipient.email}")
        self._publish(dto)

    def send_welcome_new_user(self, link: str, inviter: User):
        """Sends a welcome email to a new user"""
        dto = {
            "recipient": self.recipient.email,
            "template": EmailTemplates.WELCOME_NEW_USER,
            "template_data": {
                "first_name": self.recipient.first_name,
                "c2a_link": link,
                "inviter_name": inviter.first_name
            }
        }
        logger.info(f"Sending welcome email to {self.recipient.email} from {inviter.email}")
        self._publish(dto)

    @staticmethod
    def _publish(dto: dict) -> None:
        """ Publishes an email to SNS """
        if getenv("MOCK_AWS"):
            logger.info(f"WOULD have sent email message {dto}")
            return None

        try:
            email_sns_topic.publish(
                TopicArn=email_sns_topic.arn,
                Message=json.dumps({"default": json.dumps(dto)}),
                MessageStructure="json"
            )
        except Exception as e:
            logger.error(e)
