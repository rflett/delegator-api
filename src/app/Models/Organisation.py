import datetime

from app import db, app


class Organisation(db.Model):
    __tablename__ = "organisations"

    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String)
    chargebee_customer_id = db.Column("chargebee_customer_id", db.String, default=None)
    chargebee_subscription_id = db.Column("chargebee_subscription_id", db.String, default=None)
    chargebee_setup_complete = db.Column("chargebee_setup_complete", db.Boolean, default=False)
    chargebee_signup_plan = db.Column("chargebee_signup_plan", db.String)
    locked = db.Column("locked", db.DateTime)
    locked_reason = db.Column("locked_reason", db.String, default=None)
    created_at = db.Column("created_at", db.DateTime, default=datetime.datetime.utcnow)

    def __init__(
        self,
        name: str,
        chargebee_signup_plan: str = None,
        chargebee_customer_id: str = None,
        chargebee_subscription_id: str = None,
        chargebee_setup_complete: bool = False,
        locked: datetime = None,
        locked_reason: str = None,
    ):
        self.name = name
        self.chargebee_signup_plan = chargebee_signup_plan
        self.chargebee_customer_id = chargebee_customer_id
        self.chargebee_subscription_id = chargebee_subscription_id
        self.chargebee_setup_complete = chargebee_setup_complete
        self.locked = locked
        self.locked_reason = locked_reason

    def create_settings(self) -> None:
        """ Creates the settings for this user """
        from app.Services import SettingsService
        from app.Models import OrgSetting

        org_setting = OrgSetting(self.id)
        SettingsService.set_org_settings(org_setting)

    def as_dict(self):
        """
        :return: The dict repr of an Organisation object
        """
        if self.locked is None:
            locked = None
        else:
            locked = self.locked.strftime(app.config["RESPONSE_DATE_FORMAT"])

        return {
            "name": self.name,
            "chargebee_signup_plan": self.chargebee_signup_plan,
            "chargebee_customer_id": self.chargebee_customer_id,
            "chargebee_subscription_id": self.chargebee_subscription_id,
            "chargebee_setup_complete": self.chargebee_setup_complete,
            "locked": locked,
            "locked_reason": self.locked_reason,
        }
