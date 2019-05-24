import _thread
import json
import typing
from app import api_events_sns_topic, logger
from dataclasses import dataclass
from datetime import datetime


def do_publish(message: dict, event: str) -> None:
    """ Publishes an event to SNS """
    res = api_events_sns_topic.publish(
        TopicArn=api_events_sns_topic.arn,
        Message=json.dumps({
            'default': json.dumps(message)
        }),
        MessageStructure='json',
        MessageAttributes={
            'event': {
                'DataType': 'String',
                'StringValue': event
            },
            'event_class': {
                'DataType': 'String',
                'StringValue': event.split('_')[0]
            },
            'push': {
                'DataType': 'String',
                'StringValue': message.get('push', 'false')
            }
        }
    )
    logger.info(f"published event with messageid {res.get('MessageId')}")


@dataclass
class Notification(object):
    org_id: int
    event: str
    event_id: int
    event_friendly: str = ""
    push_details: typing.Union[dict, None] = None
    push: str = 'false'

    def __post_init__(self):
        self.event_time = datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")

    def publish(self) -> None:
        """ Publishes an event to SNS """
        _thread.start_new_thread(do_publish, (self.as_dict(), self.event))

    def as_dict(self) -> dict:
        """ Returns a notification as a dict, ready for SNS message """
        return {
            'org_id': self.org_id,
            'event': self.event,
            'event_id': self.event_id,
            'event_time': self.event_time,
            'event_friendly': self.event_friendly,
            'push_details': self.push_details,
            'push': self.push
        }
