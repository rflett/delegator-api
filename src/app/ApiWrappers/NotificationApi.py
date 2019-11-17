import json
import typing

import requests

from app.Exceptions import WrapperCallFailedException


class NotificationApi(object):
    def __init__(self, key: str, url: str):
        self.key = key
        self.url = url

    def send_notification(self, notification_payload: dict) -> None:
        """Send a notification"""
        try:
            r = requests.post(
                url=f"{self.url}/send",
                data=json.dumps(notification_payload),
                headers={
                    'Authorization': self.key,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Notification API - {r.status_code}")

    def silence_notifications(self, notification_payload: dict) -> None:
        """Silence notifications for a user"""
        try:
            r = requests.put(
                url=f"{self.url}/silence",
                data=json.dumps(notification_payload),
                headers={
                    'Authorization': self.key,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Notification API - {r.status_code}")

    def unsilence_notifications(self, notification_payload: dict) -> None:
        """Enable notifications for a user"""
        try:
            r = requests.delete(
                url=f"{self.url}/silence",
                data=json.dumps(notification_payload),
                headers={
                    'Authorization': self.key,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
        if r.status_code != 204:
            raise WrapperCallFailedException(f"Notification API - {r.status_code}")

    def get_silenced_option(self, user_id: int) -> typing.Union[int, None]:
        """Get the option that was selected when silencing notifications"""
        try:
            r = requests.get(
                url=f"{self.url}/silence?user_id={user_id}",
                headers={
                    'Authorization': self.key
                },
                timeout=10
            )
            if r.status_code != 200:
                raise WrapperCallFailedException(f"Notification API - {r.status_code}")
            else:
                response_body = r.json()
                return response_body.get('option')
        except Exception as e:
            raise WrapperCallFailedException(f"Notification API - {e}")
