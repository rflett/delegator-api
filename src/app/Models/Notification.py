import _thread
import json
import typing
from dataclasses import dataclass
from os import getenv

from app import logger, app_notifications_sqs


def do_push(notification_dto: dict) -> None:
    """ Publishes the notification to SNS """
    user_ids = notification_dto['user_ids']

    # ensure user_ids are always in a list
    if isinstance(user_ids, int):
        user_ids = [user_ids]

    # convert them to strings
    user_ids = [str(user_id) for user_id in user_ids]

    # set them again in the dto
    notification_dto['user_ids'] = user_ids

    if getenv('APP_ENV', 'Local') in ['Local', 'Docker']:
        logger.info(f"WOULD have pushed notification {notification_dto} to SQS for "
                    f"{len(notification_dto['user_ids'])} users.")
        return None

    app_notifications_sqs.send_message(
        MessageBody=json.dumps(notification_dto)
    )

    logger.info(f"Pushed notification {notification_dto} to SQS for "
                f"{len(notification_dto['user_ids'])} users.")


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
        _thread.start_new_thread(do_push, (self.as_dict(), ))  # this needs to be a tuple

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
