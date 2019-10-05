from flask_restplus import fields

from app import api


get_org_response_dto = api.model("Get Org Response", {
    "org_id": fields.Integer,
    "org_name": fields.String
})

update_org_response_dto = api.model("Update Org Response", {
    "org_name": fields.String
})

get_org_settings_response_dto = api.model("Get Org Settings Response", {
    "org_id": fields.Integer,
})

update_org_settings_response_dto = api.model("Get Org Settings Response", {
    "org_id": fields.Integer,
})

get_org_customer_id_response_dto = api.model("Get Org Customer ID Response", {
    "customer_id": fields.String(),
})
