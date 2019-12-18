import json
import typing
from os import getenv

import requests

from app.Exceptions import WrapperCallFailedException
from app.ApiWrappers.BaseWrapper import BaseWrapper


class NotificationApi(BaseWrapper):
    def __init__(self, jwt_secret: str, url: str):
        super().__init__(jwt_secret, url)

    def send_notification(self, notification_payload: dict) -> None:
        """Send a notification"""
        if getenv('MOCK_SERVICES'):
            return
        try:
            r = requests.post(
                url=f"{self.url}/send",
                data=json.dumps(notification_payload),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Notification API - {r.status_code}")

    def silence_notifications(self, notification_payload: dict) -> None:
        """Silence notifications for a user"""
        if getenv('MOCK_SERVICES'):
            return
        try:
            r = requests.put(
                url=f"{self.url}/silence",
                data=json.dumps(notification_payload),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Notification API - {r.status_code}")

    def unsilence_notifications(self, notification_payload: dict) -> None:
        """Enable notifications for a user"""
        if getenv('MOCK_SERVICES'):
            return
        try:
            r = requests.delete(
                url=f"{self.url}/silence",
                data=json.dumps(notification_payload),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Notification API - {r.status_code}")

    def get_silenced_option(self, user_id: int) -> typing.Union[int, None]:
        """Get the option that was selected when silencing notifications"""
        if getenv('MOCK_SERVICES'):
            return

        try:
            r = requests.get(
                url=f"{self.url}/silence?user_id={user_id}",
                headers={
                    'Authorization': f"Bearer {self.create_sa_token()}"
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
        if r.status_code != 200:
            raise WrapperCallFailedException(f"Notification API - {r.status_code}")
        else:
            return r.json()
