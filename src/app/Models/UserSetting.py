from dataclasses import dataclass
from decimal import Decimal
from os import getenv

import boto3
from boto3.dynamodb.conditions import Key
from flask import current_app

dyn_db = boto3.resource("dynamodb")


@dataclass
class UserSetting:
    """ User settings model"""

    user_id: Decimal

    def as_dict(self):
        return {"user_id": int(self.user_id)}

    def update(self):
        """ Updates DynamoDB table with UserSetting as dict"""
        if getenv("MOCK_AWS"):
            return
        # TODO should be changed to update_item
        self._table().put_item(Item=self.as_dict(), ReturnValues="NONE")

    @staticmethod
    def get():
        """ Returns user settings from DynamoDB as a UserSetting object """
        if getenv("MOCK_AWS"):
            return

        return
        # settings_obj = (
        #     self._table()
        #     .query(Select="ALL_ATTRIBUTES", KeyConditionExpression=Key("user_id").eq(self.user_id))
        #     .get("Items")[0]
        # )
        # self.profile_picture_uuid = settings_obj.get("profile_picture_uuid")

    @staticmethod
    def _table():
        return dyn_db.Table(current_app.config["USER_SETTINGS_TABLE"])
