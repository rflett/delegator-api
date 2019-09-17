from flask_restplus import fields

from app import api


update_org_request = api.model("Update Org Request", {
    "org_id": fields.Integer(),
    "org_name": fields.String()
})

update_org_subscription_request = api.model("Update Org Subscription Request", {
    "chargebee_customer_id": fields.String(),
    "plan_id": fields.String()
})

lock_org_request = api.model("Lock Org Request", {
    "locked_reason": fields.String()
})

update_org_settings_request = api.model("Update Org Settings Request", {
    "org_id": fields.Integer()
})
