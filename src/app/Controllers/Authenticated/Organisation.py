import datetime
from decimal import Decimal

import structlog
from flask import request
from flask_restx import Namespace, fields
from sqlalchemy import exists, and_, func


from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError
from app.Models import OrgSetting
from app.Models.Dao import Organisation
from app.Models.Enums import Operations, Resources, Roles

api = Namespace(path="/org", name="Organisation", description="Manage the organisation")
log = structlog.getLogger()


class NullableString(fields.String):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "nullable string"


@api.route("/")
class OrganisationManage(RequestValidationController):

    get_org_response_dto = api.model("Get Org Response", {"org_id": fields.Integer(), "org_name": fields.String()})

    @requires_jwt
    @authorize(Operations.GET, Resources.ORGANISATION)
    @api.marshal_with(get_org_response_dto, code=200)
    def get(self, **kwargs):
        """Get an organisation"""
        req_user = kwargs["req_user"]
        req_user.log(Operations.GET, Resources.ORGANISATION)
        org = req_user.orgs
        return {"org_id": org.id, "org_name": org.name}, 200

    update_org_request = api.model("Update Org Request", {"org_name": fields.String(required=True)})
    update_org_response = api.model("Update Org Response", {"org_name": fields.String()})

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.ORGANISATION)
    @api.expect(update_org_request, validate=True)
    @api.marshal_with(update_org_response, code=200)
    def put(self, **kwargs):
        """Update an organisation"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()
        org_name = request_body["org_name"]

        # check an org with that name doesn't exist already
        with session_scope() as session:
            if session.query(
                exists().where(
                    and_(
                        func.lower(Organisation.name) == func.lower(request_body["org_name"]),
                        Organisation.id != req_user.org_id,
                    )
                )
            ).scalar():
                raise ValidationError("That organisation name already exists.")

        with session_scope():
            req_user.orgs.name = org_name

        req_user.log(Operations.UPDATE, Resources.ORGANISATION)
        return {"org_name": req_user.orgs.name}, 200


@api.route("/settings")
class OrganisationSettings(RequestValidationController):
    customer_task_field = api.model(
        "Custom Task Field", {"custom_1": NullableString(), "custom_2": NullableString(), "custom_3": NullableString()}
    )
    get_org_settings_response = api.model(
        "Get Org Settings Response",
        {"org_id": fields.Integer(), "custom_task_fields": fields.Nested(customer_task_field)},
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.ORG_SETTINGS)
    @api.marshal_with(get_org_settings_response, code=200)
    def get(self, **kwargs):
        """Get an organisation's settings"""
        req_user = kwargs["req_user"]
        req_user.log(Operations.GET, Resources.ORG_SETTINGS)
        org_setting = OrgSetting(req_user.org_id)
        org_setting.get()
        return org_setting, 200

    update_org_settings_request = api.model(
        "Update Org Settings Request",
        {
            "org_id": fields.Integer(required=True),
            "custom_task_fields": fields.Nested(customer_task_field, required=True),
        },
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.ORG_SETTINGS)
    @api.expect(update_org_settings_request, validate=True)
    @api.marshal_with(get_org_settings_response, code=200)
    def put(self, **kwargs):
        """Update an organisation's settings"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        org_setting = OrgSetting(Decimal(req_user.org_id))

        org_setting.custom_task_fields = request_body["custom_task_fields"]
        org_setting.update()

        req_user.log(Operations.UPDATE, Resources.ORG_SETTINGS, resource_id=req_user.org_id)
        return org_setting.as_dict(), 200


@api.route("/lock/<string:customer_id>")
class OrganisationLock(RequestValidationController):

    lock_org_request = api.model("Lock Org Request", {"locked_reason": fields.String(required=True)})

    @requires_jwt
    @authorize(Operations.LOCK, Resources.ORGANISATION)
    @api.expect(lock_org_request, validate=True)
    @api.response(204, "Success")
    def put(self, customer_id: str, **kwargs):
        """Lock an organisation due to a billing issue."""
        req_user = kwargs["req_user"]

        locked_reason = request.get_json().get("locked_reason")
        with session_scope() as session:
            # get the org from the customer id
            org = session.query(Organisation).filter_by(chargebee_customer_id=customer_id).first()
            if org is None:
                raise ValidationError(f"Org with customer_id {customer_id} doesn't exist")
            else:
                # set the users old role
                session.execute(
                    """
                    UPDATE users
                    SET role_before_locked = role
                    WHERE org_id = :org_id
                    """,
                    {"org_id": org.id},
                )
                # lock users
                session.execute(
                    """
                    UPDATE users
                    SET role = :role
                    WHERE org_id = :org_id
                    """,
                    {"org_id": org.id, "role": Roles.LOCKED},
                )
                # lock org
                org.locked = datetime.datetime.utcnow()
                org.locked_reason = locked_reason

        req_user.log(Operations.LOCK, Resources.ORGANISATION, org.id)
        return "", 204

    @requires_jwt
    @authorize(Operations.UNLOCK, Resources.ORGANISATION)
    @api.response(204, "Success")
    def delete(self, customer_id: str, **kwargs):
        """Unlock an organisation after the billing issue has been rectified"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            # get the org from the customer id
            org = session.query(Organisation).filter_by(chargebee_customer_id=customer_id).first()
            if org is None:
                raise ValidationError(f"Org with customer_id {customer_id} doesn't exist")
            elif org.locked is None:
                raise ValidationError("Org hasn't been locked")
            else:
                # set the users role to their role before they were locked
                session.execute(
                    """
                    UPDATE users
                    SET role = role_before_locked
                    WHERE org_id = :org_id
                    AND role_before_locked IS NOT NULL
                    """,
                    {"org_id": org.id},
                )
                # clear old locked role
                session.execute(
                    """
                    UPDATE users
                    SET role_before_locked = NULL
                    WHERE org_id = :org_id
                    """,
                    {"org_id": org.id},
                )
                # lock org
                org.locked = None

        req_user.log(Operations.UNLOCK, Resources.ORGANISATION, org.id)
        return "", 204


@api.route("/subscription")
class OrganisationSubscription(RequestValidationController):

    request = api.model(
        "Update Org Subscription Request",
        {"customer_id": fields.String(required=True), "subscription_id": fields.String(required=True)},
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.ORGANISATION_SUBSCRIPTION)
    @api.expect(request, validate=True)
    @api.response(200, "Success")
    def put(self, **kwargs):
        """Set the subscription_id for an org"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()
        customer_id = request_body["customer_id"]
        subscription_id = request_body["subscription_id"]

        with session_scope() as session:
            org = session.query(Organisation).filter_by(chargebee_customer_id=customer_id).first()
            if org is None:
                raise ValidationError(f"There is no organisation with customer id {customer_id}")
            else:
                # check subscription_id matches
                if not org.chargebee_subscription_id == subscription_id:
                    log.error(
                        f"org subscription id {org.chargebee_subscription_id} doesn't match "
                        f"subscription_id in the request {subscription_id}"
                    )
                    raise ValidationError("subscription_id already against organisation doesn't match request")
                else:
                    org.chargebee_setup_complete = True
                    req_user.log(Operations.UPDATE, Resources.ORGANISATION_SUBSCRIPTION, org.id)
                    log.info(f"Org {org.name} has completed chargebee setup")
                    return "", 204


@api.route("/customer")
class OrgCustomerId(RequestValidationController):

    response = api.model("Get Org Customer ID Response", {"customer_id": fields.String()})

    @requires_jwt
    @authorize(Operations.GET, Resources.ORGANISATION_SUBSCRIPTION)
    @api.marshal_with(response, code=200)
    def get(self, **kwargs):
        """Get the customer_id for an org"""
        req_user = kwargs["req_user"]
        return {"customer_id": req_user.orgs.chargebee_customer_id}, 200
