from dataclasses import dataclass, field
from decimal import Decimal
from os import getenv

import boto3
from boto3.dynamodb.conditions import Key
from flask import current_app

dyn_db = boto3.resource("dynamodb")


@dataclass
class OrgSetting:
    """ Org settings model"""

    org_id: Decimal
    custom_task_fields: dict = None

    def as_dict(self):
        return {"org_id": int(self.org_id), "custom_task_fields": self.custom_task_fields}

    def update(self):
        """ Updates DynamoDB table with UserSetting as dict"""
        if getenv("MOCK_AWS"):
            return
        self._table().put_item(Item=self.as_dict(), ReturnValues="NONE")

    def get(self):
        """ Returns user settings from DynamoDB as a UserSetting object """
        if getenv("MOCK_AWS"):
            return

        settings_obj = (
            self._table()
            .query(Select="ALL_ATTRIBUTES", KeyConditionExpression=Key("org_id").eq(self.org_id))
            .get("Items")[0]
        )
        self.custom_task_fields = settings_obj.get("custom_task_fields")

    @staticmethod
    def _table():
        return dyn_db.Table(current_app.config["ORG_SETTINGS_TABLE"])
