from decimal import Decimal
from os import getenv

from boto3.dynamodb.conditions import Key

from app import user_settings_table, org_settings_table
from app.Models import UserSetting, OrgSetting


class SettingsService(object):
    @staticmethod
    def get_user_settings(user_id: int) -> UserSetting:
        """ Returns user settings from DynamoDB as a UserSetting object """
        if getenv('MOCK_AWS'):
            return UserSetting(Decimal(user_id))

        settings_obj = user_settings_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('user_id').eq(user_id)
        ).get('Items')[0]
        return UserSetting(**settings_obj)

    @staticmethod
    def set_user_settings(settings: UserSetting) -> None:
        """ Updates DynamoDB table with UserSetting as dict"""
        if getenv('MOCK_AWS'):
            return
        # TODO should be changed to update_item
        user_settings_table.put_item(
            Item=settings.as_dict(),
            ReturnValues='NONE'
        )

    @staticmethod
    def get_org_settings(org_id: int) -> OrgSetting:
        """ Returns org settings from DynamoDB as a UserSetting object """
        if getenv('MOCK_AWS'):
            return OrgSetting(Decimal(org_id))

        settings_obj = org_settings_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('org_id').eq(org_id)
        ).get('Items')[0]
        return OrgSetting(**settings_obj)

    @staticmethod
    def set_org_settings(settings: OrgSetting) -> None:
        """ Updates DynamoDB table with OrgSetting as dict"""
        if getenv('MOCK_AWS'):
            return
        # TODO should be changed to update_item
        org_settings_table.put_item(
            Item=settings.as_dict(),
            ReturnValues='NONE'
        )
