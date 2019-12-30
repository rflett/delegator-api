import json
from os import getenv

import requests

from app import logger
from app.ApiWrappers import BaseWrapper


class EmailApi(BaseWrapper):
    def __init__(self, jwt_secret: str, url: str):
        super().__init__(jwt_secret, url)

    def send_welcome(self, email: str, first_name: str) -> None:
        """Get a subscription's plan quantity"""
        if getenv('MOCK_SERVICES'):
            return
        try:
            r = requests.post(
                url=f"{self.url}/send/welcome",
                headers={
                    'Authorization': f"Bearer {self.create_sa_token()}",
                    'Content-Type': 'application/json'
                },
                data=json.dumps({
                  "recipient": email,
                  "template_data": {
                    "first_name": first_name
                  }
                }),
                timeout=10
            )
            if r.status_code != 204:
                logger.error(f"Email API - {r.status_code}, {r.content}")
        except Exception as e:
            logger.error(f"Email API - {e}")

    def send_reset_password(self, email: str, first_name: str, link: str) -> None:
        """Get a subscription's plan quantity"""
        if getenv('MOCK_SERVICES'):
            return
        try:
            r = requests.post(
                url=f"{self.url}/send/reset-password",
                headers={
                    'Authorization': f"Bearer {self.create_sa_token()}",
                    'Content-Type': 'application/json'
                },
                data=json.dumps({
                  "recipient": email,
                  "template_data": {
                    "first_name": first_name,
                    "link": link
                  }
                }),
                timeout=10
            )
            if r.status_code != 204:
                logger.error(f"Email API - {r.status_code}, {r.content}")
        except Exception as e:
            logger.error(f"Email API - {e}")
