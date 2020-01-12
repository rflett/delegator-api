import json
from dataclasses import dataclass
from datetime import datetime
from os import getenv

from app import api_events_sns_topic, app, logger, app_env


@dataclass
class Activity(object):
    org_id: int
    event: str
    event_id: int
    event_friendly: str = ""

    def __post_init__(self):
        self.event_time = datetime.utcnow().strftime(app.config["DYN_DB_ACTIVITY_DATE_FORMAT"])

    def publish(self) -> None:
        """ Publishes an event to SNS """
        if app_env in ["Local"] or getenv("MOCK_AWS"):
            logger.info(f"WOULD have published message {self.event}")
            return None

        api_events_sns_topic.publish(
            TopicArn=api_events_sns_topic.arn,
            Message=json.dumps({"default": json.dumps(self.as_dict())}),
            MessageStructure="json",
            MessageAttributes={
                "event": {"DataType": "String", "StringValue": self.event},
                "event_class": {"DataType": "String", "StringValue": self.event.split("_")[0]},
            },
        )

    def as_dict(self) -> dict:
        """ Returns an activity as a dict, ready for SNS message """
        return {
            "org_id": self.org_id,
            "event": self.event,
            "event_id": self.event_id,
            "event_time": self.event_time,
            "event_friendly": self.event_friendly,
        }
