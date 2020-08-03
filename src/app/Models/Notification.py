import datetime
import json
import typing
import uuid
from dataclasses import dataclass, field
from os import getenv

import jwt
import requests
import structlog
from flask import current_app

log = structlog.getLogger()


@dataclass
class NotificationAction:
    label: str
    icon: str  # The icon name without extension to use for this action

    def as_dict(self) -> dict:
        """ Returns dict repr of a NotificationAction """
        return {
            "label": self.label,
            "icon": self.icon,
        }


@dataclass
class Notification(object):
    title: str
    event_name: str
    msg: str
    target_type: str
    target_id: int
    actions: typing.List[NotificationAction]
    user_ids: typing.List[int] = field(default=list)

    def push(self) -> None:
        """ Publish the message to SNS for pushing to the user """
        if getenv("MOCK_SERVICES"):
            log.info(f"WOULD have pushed notification {self.as_dict()} to NotificationApi")
            return
        try:
            r = requests.post(
                url=f"{current_app.config['NOTIFICATION_API_PUBLIC_URL']}/notifications/send/",
                data=json.dumps(self.as_dict()),
                headers={"Content-Type": "application/json", "Authorization": self._jwt_token()},
                timeout=10,
            )
            if r.status_code != 204:
                log.error(f"there was an issue sending the notification {self.as_dict()}")
        except requests.exceptions.RequestException:
            log.error(f"there was an issue sending the notification {self.as_dict()}")

    def as_dict(self) -> dict:
        """ Returns a notification as a dict, ready for SNS message """
        return {
            "title": self.title,
            "event_name": self.event_name,
            "msg": self.msg,
            "target_type": self.target_type,
            "target_id": str(self.target_id),  # SNS can't use ints
            "actions": [a.as_dict() for a in self.actions],
            "user_ids": self.user_ids,
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
