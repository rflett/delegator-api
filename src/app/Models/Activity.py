import json
from dataclasses import dataclass
from datetime import datetime
from os import getenv

import boto3
from flask import current_app

sns = boto3.resource("sns")


@dataclass
class Activity(object):
    org_id: int
    event: str
    event_id: int
    event_friendly: str = ""

    def __post_init__(self):
        self.event_time = datetime.utcnow().strftime(current_app.config["DYN_DB_ACTIVITY_DATE_FORMAT"])

    def publish(self) -> None:
        """ Publishes an event to SNS """
        if getenv("MOCK_AWS"):
            current_app.logger.info(f"WOULD have published message {self.as_dict()}")
            return None

        api_events_sns_topic = sns.Topic(current_app.config["EVENTS_SNS_TOPIC_ARN"])
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
