import datetime
import json
import typing
import uuid
from dataclasses import dataclass, field
from os import getenv

import jwt
from flask import current_app
import requests


@dataclass
class NotificationAction:
    label: str
    target_id: int
    target_type: str

    def as_dict(self) -> dict:
        """ Returns dict repr of a NotificationAction """
        return {
            "label": self.label,
            "target_id": str(self.target_id),  # sns can't have integers
            "target_type": self.target_type
        }


@dataclass
class Notification(object):
    event_name: str
    title: str
    msg: str
    actions: typing.List[NotificationAction]
    user_ids: typing.List[int] = field(default=list)

    def push(self) -> None:
        """ Publish the message to SNS for pushing to the user """
        if getenv("MOCK_SERVICES"):
            current_app.logger.info(f"WOULD have pushed notification {self.as_dict()} to NotificationApi")
            return
        try:
            r = requests.post(
                url=f"{current_app.config['NOTIFICATION_API_PUBLIC_URL']}/notifications/send/",
                data=json.dumps(self.as_dict()),
                headers={"Content-Type": "application/json", "Authorization": self._jwt_token()},
                timeout=10,
            )
            if r.status_code != 204:
                current_app.logger.error(f"there was an issue sending the notification {self.as_dict()}")
        except requests.exceptions.RequestException:
            current_app.logger.error(f"there was an issue sending the notification {self.as_dict()}")

    def as_dict(self) -> dict:
        """ Returns a notification as a dict, ready for SNS message """
        return {
            "event_name": self.event_name,
            "user_ids": self.user_ids,
            "title": self.title,
            "msg": self.msg,
            "icon_url": "https://assets.delegator.com.au/web/logos/simple_colour.png",
            "actions": [a.as_dict() for a in self.actions]
        }

    @staticmethod
    def _jwt_token():
        """Create a new JWT token"""
        token = jwt.encode(
            payload={
                "claims": {"type": "service-account", "service-account-name": "delegator-api"},
                "jti": str(uuid.uuid4()),
                "aud": "delegator.com.au",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=30),
            },
            key=current_app.config["JWT_SECRET"],
            algorithm="HS256",
        ).decode("utf-8")
        return "Bearer " + token
