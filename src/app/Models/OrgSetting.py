from dataclasses import dataclass
from decimal import Decimal
from os import getenv

import boto3
from flask import current_app

dyn_db = boto3.resource("dynamodb")


@dataclass
class OrgSetting:
    """ Org settings model"""

    org_id: Decimal

    def as_dict(self):
        return {"org_id": int(self.org_id)}

    @staticmethod
    def update():
        """ Updates DynamoDB table with UserSetting as dict"""
        if getenv("MOCK_AWS"):
            return
        else:
            pass

    @staticmethod
    def get():
        """ Returns user settings from DynamoDB as a UserSetting object """
        if getenv("MOCK_AWS"):
            return
        else:
            pass

    @staticmethod
    def _table():
        return dyn_db.Table(current_app.config["ORG_SETTINGS_TABLE"])
