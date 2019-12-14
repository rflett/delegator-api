import typing
from dataclasses import dataclass

from app import notification_api, logger, app_env


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
        if app_env == 'Local':
            logger.info(f"WOULD have pushed notification {self.as_dict()} to NotificationApi")
            return None
        notification_api.send_notification(self.as_dict())

    def as_dict(self) -> dict:
        """ Returns a notification as a dict, ready for SNS message """
        return {
            "title": self.title,
            "event_name": self.event_name,
            "msg": self.msg,
            "user_ids": self.user_ids,
            "click_action": self.click_action,
            "action_ids": {
                "user_id": self.user_action_id,
                "task_id": self.task_action_id
            }
        }
