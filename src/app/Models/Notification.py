import json
from app import api_events_sns_topic, logger
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Notification(object):
    org_id: int
    event: str
    payload: dict

    def __post_init__(self):
        self.event_time = datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")

    def publish(self) -> None:
        """ Publishes an event to SNS """
        res = api_events_sns_topic.publish(
            TopicArn=api_events_sns_topic.arn,
            Message=json.dumps({
                'default': json.dumps(self.as_dict())
            }),
            MessageStructure='json'
        )
        logger.info(f"published event with messageid {res.get('MessageId')}")

    def as_dict(self) -> dict:
        """ Returns a notification as a dict, ready for SNS message """
        return {
            'org_id': self.org_id,
            'event': self.event,
            'payload': self.payload,
            'event_time': self.event_time
        }
