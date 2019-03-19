from app import user_settings_table, org_settings_table
from app.Models import UserSetting, OrgSetting
from boto3.dynamodb.conditions import Attr


class SettingsController(object):
    @staticmethod
    def get_user_settings(user_id: int) -> UserSetting:
        settings_obj = user_settings_table.scan(
            FilterExpression=Attr('user_id').eq(user_id)
        ).get('Items')[0]
        return UserSetting(**settings_obj)

    @staticmethod
    def set_user_settings(settings: UserSetting) -> None:
        user_settings_table.put_item(
            Item=settings.as_dict(),
            ReturnValues='NONE'
        )

    @staticmethod
    def get_org_settings(org_id: int) -> OrgSetting:
        settings_obj = org_settings_table.scan(
            FilterExpression=Attr('org_id').eq(org_id)
        ).get('Items')[0]
        return OrgSetting(**settings_obj)

    @staticmethod
    def set_org_settings(settings: OrgSetting) -> None:
        org_settings_table.put_item(
            Item=settings.as_dict(),
            ReturnValues='NONE'
        )