import boto3
from botocore.exceptions import ClientError

from app import app, logger


class EmailService(object):
    def send_invite_email(self, recipient: str, token: str) -> None:
        """Sends an email for someone to setup their password for the first time
        Copy pasta from https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-using-sdk-python.html
        """
        # The subject line for the email.
        subject = "Delegator - Account validation and setup"

        # The email body for recipients with non-HTML email clients.
        body_text = ("Delegator - account validation\r\n"
                     "Please use the following one-time link to set "
                     f"your password {app.config['DELEGATOR_API_URL']}?invtkn={token}"
                     )

        # The HTML body of the email.
        body_html = f"""
        <html>
            <head></head>
            <body>
              <h1>Delegator Account Validation</h1>
              <p>Please click the following one time link to activate your account and set your password:
                <a href='{app.config['DELEGATOR_API_URL']}?invtkn={token}'>
                    {app.config['DELEGATOR_API_URL']}?invtkn={token}
                </a>
              </p>
            </body>
        </html>
        """

        self._send_mail("ryan.flett@delegator.com.au", subject, body_text, body_html)

    def send_reset_password_email(self, recipient: str, token: str) -> None:
        """Sends an email for someone to reset their password
        Copy pasta from https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-using-sdk-python.html
        """
        # The subject line for the email.
        subject = "Delegator - Password reset requested"

        # The email body for recipients with non-HTML email clients.
        body_text = ("Delegator - Password reset requested\r\n"
                     "Please use the following one-time link to reset "
                     f"your password {app.config['DELEGATOR_API_URL']}?invtkn={token}"
                     )

        # The HTML body of the email.
        body_html = f"""
        <html>
            <head></head>
            <body>
              <h1>Delegator - Password reset requested</h1>
              <p>Please click the following one time link to reset your password:
                <a href='{app.config['DELEGATOR_API_URL']}?invtkn={token}'>
                    {app.config['DELEGATOR_API_URL']}?invtkn={token}
                </a>
              </p>
            </body>
        </html>
        """

        self._send_mail("ryan.flett@delegator.com.au", subject, body_text, body_html)

    @staticmethod
    def _send_mail(recipient: str, subject: str, body_text: str, body_html: str) -> None:
        # The character encoding for the email.
        charset = "UTF-8"

        # client setup
        ses = boto3.client("ses")

        try:
            # Provide the contents of the email.
            response = ses.send_email(
                Destination={
                    'ToAddresses': [
                        recipient,
                    ],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': charset,
                            'Data': body_html,
                        },
                        'Text': {
                            'Charset': charset,
                            'Data': body_text,
                        },
                    },
                    'Subject': {
                        'Charset': charset,
                        'Data': subject,
                    },
                },
                Source="ryan.flett@delegator.com.au"
            )
        # Display an error if something goes wrong.
        except ClientError as e:
            logger.error(e.response['Error']['Message'])
        else:
            logger.info(f"Email sent! Message ID: {response['MessageId']}")
