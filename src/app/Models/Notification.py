import _thread
import json
import typing
from dataclasses import dataclass
from os import getenv

from app import logger, app_notifications_sqs


def do_push(msg: str, user_ids: typing.Union[int, typing.List[int]]) -> None:
    """ Publishes the notification to SNS """
    if isinstance(user_ids, int):
        user_ids = [user_ids]

    if getenv('APP_ENV', 'Local') == 'Local':
        logger.info(f"WOULD have pushed notification to SQS for {len(user_ids)} users.")
        return None

    app_notifications_sqs.send_message(
        MessageBody=json.dumps({
            "msg": msg,
            "user_ids": user_ids
        })
    )

    logger.info(f"Pushed notification to SQS for {len(user_ids)} users.")


@dataclass
class Notification(object):
    msg: str
    user_ids: typing.Union[int, typing.List[int]]

    def push(self) -> None:
        """ Publish the message to SNS for pushing to the user """
        _thread.start_new_thread(do_push, (self.msg, self.user_ids))

    def as_dict(self) -> dict:
        """ Returns a notification as a dict, ready for SNS message """
        return {
            'msg': self.msg,
            'user_ids': self.user_ids,
        }
