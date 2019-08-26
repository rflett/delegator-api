import binascii
import datetime
import hashlib
import uuid

from app import db


class Organisation(db.Model):
    __tablename__ = "organisations"

    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String)
    product_tier = db.Column('product_tier', db.Integer, db.ForeignKey('product_tiers.plan_id'), default=None)
    chargebee_customer_id = db.Column('chargebee_customer_id', db.String, default=None)
    chargebee_subscription_id = db.Column('chargebee_subscription_id', db.String, default=None)
    jwt_aud = db.Column('jwt_aud', db.String)
    jwt_secret = db.Column('jwt_secret', db.String)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)

    # TODO remove the need for this - replace with HTTP call to subscription-api
    product_tiers = db.relationship("ProductTier", backref="organisations")

    def __init__(self,
                 name: str,
                 product_tier: str = None,
                 chargebee_customer_id: str = None,
                 chargebee_subscription_id: str = None):
        self.name = name
        self.product_tier = product_tier
        self.chargebee_customer_id = chargebee_customer_id
        self.chargebee_subscription_id = chargebee_subscription_id
        self.jwt_aud = str(uuid.uuid4())
        self.jwt_secret = binascii.hexlify(
            hashlib.pbkdf2_hmac('sha256', uuid.uuid4().bytes, uuid.uuid4().bytes, 100000)).decode('ascii')

    def create_settings(self) -> None:
        """ Creates the settings for this user """
        from app.Controllers.SettingsController import SettingsController
        from app.Models import OrgSetting
        SettingsController.set_org_settings(OrgSetting(self.id))

    def as_dict(self):
        """
        :return: The dict repr of an Organisation object
        """
        return {
            "name": self.name,
            "product_tier": self.product_tier,
            "chargebee_customer_id": self.chargebee_customer_id,
            "chargebee_subscription_id": self.chargebee_subscription_id
        }
