from flask_restplus import fields

from app import api


update_org_dto = api.model("Update Org Model", {
    "org_id": fields.Integer,
    "org_name": fields.String
})

update_org_subscription_dto = api.model("Update Org Subscription Model", {
    "chargebee_customer_id": fields.String,
    "plan_id": fields.String
})

lock_org_dto = api.model("Lock Org Model", {
    "locked_reason": fields.String
})

update_org_settings_dto = api.model("Update Org Settings Model", {
    "org_id": fields.Integer
})
