import json

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
