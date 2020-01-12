import datetime

from flask import request, Response
from flask_restplus import Namespace


from app import session_scope, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Exceptions import ValidationError
from app.Models import Organisation
from app.Models.Enums import Operations, Resources
from app.Models.Response import update_org_response_dto, update_org_settings_response_dto, \
    get_org_settings_response_dto, get_org_response_dto, message_response_dto, get_org_customer_id_response_dto
from app.Models.Request import lock_org_request, update_org_subscription_request, update_org_settings_request, \
    update_org_request
from app.Services import SettingsService

org_route = Namespace(
    path="/org",
    name="Organisation",
    description="Manage the organisation"
)

settings_service = SettingsService()


@org_route.route("/")
class OrganisationManage(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.ORGANISATION)
    @org_route.response(200, "Success", get_org_response_dto)
    @org_route.response(403, "Insufficient privileges", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Get an organisation"""
        req_user = kwargs['req_user']

        req_user.log(
            operation=Operations.GET,
            resource=Resources.ORGANISATION
        )

        org = req_user.orgs

        return self.ok({
            "org_id": org.id,
            "org_name": org.name
        })

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.ORGANISATION)
    @org_route.expect(update_org_request)
    @org_route.response(200, "Success", update_org_response_dto)
    @org_route.response(400, "Failed to update the organisation", message_response_dto)
    @org_route.response(403, "Insufficient privileges", message_response_dto)
    @org_route.response(404, "Organisation does not exist", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Update an organisation"""
        req_user = kwargs['req_user']

        org_name = self.validate_update_org_request(req_user, request.get_json())

        with session_scope():
            req_user.orgs.name = org_name

        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.ORGANISATION
        )
        return self.ok({
            "org_name": req_user.orgs.name
        })


@org_route.route("/settings")
class OrganisationSettings(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.ORG_SETTINGS)
    @org_route.response(200, "Success", get_org_settings_response_dto)
    @org_route.response(403, "Insufficient privileges", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Get an organisation's settings"""
        req_user = kwargs['req_user']
        req_user.log(
            operation=Operations.GET,
            resource=Resources.ORG_SETTINGS
        )
        return self.ok(settings_service.get_org_settings(req_user.org_id).as_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.ORG_SETTINGS)
    @org_route.expect(update_org_settings_request)
    @org_route.response(200, "Success", update_org_settings_response_dto)
    @org_route.response(400, "Failed to update the organisation", message_response_dto)
    @org_route.response(403, "Insufficient privileges", message_response_dto)
    @org_route.response(404, "Organisation does not exist", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Update an organisation's settings"""
        req_user = kwargs['req_user']
        org_setting = self.validate_update_org_settings_request(req_user.org_id, request.get_json())
        settings_service.set_org_settings(org_setting)
        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.ORG_SETTINGS,
            resource_id=req_user.org_id
        )
        return self.ok(settings_service.get_org_settings(req_user.org_id).as_dict())


@org_route.route("/lock/<string:customer_id>")
class OrganisationLock(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.LOCK, Resources.ORGANISATION)
    @org_route.expect(lock_org_request)
    @org_route.response(200, "Locked the organisation", message_response_dto)
    @org_route.response(403, "Insufficient privileges", message_response_dto)
    @org_route.response(404, "Organisation does not exist", message_response_dto)
    def put(self, customer_id: str, **kwargs) -> Response:
        """Lock an organisation due to a billing issue."""
        req_user = kwargs['req_user']

        locked_reason = request.get_json().get('locked_reason')
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
                    {'org_id': org.id}
                )
                # lock users
                session.execute(
                    """
                    UPDATE users
                    SET role = 'LOCKED'
                    WHERE org_id = :org_id
                    """,
                    {'org_id': org.id}
                )
                # lock org
                org.locked = datetime.datetime.utcnow()
                org.locked_reason = locked_reason

        req_user.log(Operations.LOCK, Resources.ORGANISATION, org.id)
        return self.ok(f"Successfully locked org {org.id}")

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UNLOCK, Resources.ORGANISATION)
    @org_route.response(200, "Success", message_response_dto)
    @org_route.response(403, "Insufficient privileges", message_response_dto)
    @org_route.response(404, "Organisation does not exist", message_response_dto)
    def delete(self, customer_id: str, **kwargs) -> Response:
        """Unlock an organisation after the billing issue has been rectified"""
        req_user = kwargs['req_user']

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
                    {'org_id': org.id}
                )
                # clear old locked role
                session.execute(
                    """
                    UPDATE users
                    SET role_before_locked = NULL
                    WHERE org_id = :org_id
                    """,
                    {'org_id': org.id}
                )
                # lock org
                org.locked = None

        req_user.log(Operations.UNLOCK, Resources.ORGANISATION, org.id)
        return self.ok(f"Successfully unlocked org {org.id}")


@org_route.route("/subscription")
class OrganisationSubscription(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.ORGANISATION_SUBSCRIPTION)
    @org_route.expect(update_org_subscription_request)
    @org_route.response(200, "Success", message_response_dto)
    @org_route.response(400, "Failed to update the organisation's subscription", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Set the subscription_id for an org"""
        req_user = kwargs['req_user']

        try:
            request_body = request.get_json()
            customer_id = request_body['customer_id']
            subscription_id = request_body['subscription_id']
        except KeyError as e:
            raise ValidationError(f"Missing {e} from request")

        with session_scope() as session:
            org = session.query(Organisation).filter_by(chargebee_customer_id=customer_id).first()
            if org is None:
                raise ValidationError(f"There is no organisation with customer id {customer_id}")
            else:
                # check subscription_id matches
                if not org.chargebee_subscription_id == subscription_id:
                    logger.error("subscription_id already against organisation doesn't match webhook")
                    raise ValidationError("subscription_id already against organisation doesn't match webhook")
                else:
                    org.chargebee_setup_complete = True
                    req_user.log(Operations.UPDATE, Resources.ORGANISATION_SUBSCRIPTION, org.id)
                    logger.info(f"Org {org.name} has completed chargebee setup")
                    return self.ok(f"Completed chargebee setup for org {org.name}")


@org_route.route("/customer")
class OrgCustomerId(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @org_route.response(200, "Success", get_org_customer_id_response_dto)
    @org_route.response(400, "Failed to update the organisation's subscription", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Get the customer_id for an org"""
        req_user = kwargs['req_user']
        return self.ok({"customer_id": req_user.orgs.chargebee_customer_id})
