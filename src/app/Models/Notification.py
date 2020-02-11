import datetime
import json
import typing
import uuid
from dataclasses import dataclass

import jwt
from flask import current_app
import requests

from app import logger, app_env


@dataclass
class Notification(object):
    title: str
    event_name: str
    msg: str
    user_ids: typing.Union[int, typing.List[int]] = None
    click_action: str = None
    user_action_id: int = None
    task_action_id: int = None

    def push(self) -> None:
        """ Publish the message to SNS for pushing to the user """
        if app_env == "Local":
            logger.info(f"WOULD have pushed notification {self.as_dict()} to NotificationApi")
            return None

        try:
            r = requests.post(
                url=f"{current_app.config['NOTIFICATION_API_PUBLIC_URL']}/notifications/send/",
                data=json.dumps(self.as_dict()),
                headers={"Content-Type": "application/json", "Authorization": self._jwt_token()},
                timeout=10,
            )
            if r.status_code != 204:
                logger.error(f"there was an issue sending the notification {self.as_dict()}")
        except requests.exceptions.RequestException:
            logger.error(f"there was an issue sending the notification {self.as_dict()}")

    def as_dict(self) -> dict:
        """ Returns a notification as a dict, ready for SNS message """
        # always set user_ids to be a list
        if isinstance(self.user_ids, int):
            user_ids = [self.user_ids]
        else:
            user_ids = self.user_ids

        return {
            "title": self.title,
            "event_name": self.event_name,
            "msg": self.msg,
            "user_ids": user_ids,
            "click_action": self.click_action,
            "action_ids": {"user_id": self.user_action_id, "task_id": self.task_action_id},
        }

    @staticmethod
    def _jwt_token():
        """Create a new JWT token"""
        token = jwt.encode(
            payload={
                "claims": {"type": "service-account", "service-account-name": "subscription-api"},
                "jti": str(uuid.uuid4()),
                "aud": "delegator.com.au",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=30),
            },
            key=current_app.config["JWT_SECRET"],
            algorithm="HS256",
        ).decode("utf-8")
        return "Bearer " + token
