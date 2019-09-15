import datetime

from flask import request, Response


from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Exceptions import ValidationError
from app.Models import Organisation
from app.Models.Enums import Operations, Resources
from app.Services import SettingsService


class OrganisationController(RequestValidationController):
    settings_service: SettingsService = None

    def __init__(self):
        RequestValidationController.__init__(self)
        self.settings_service = SettingsService()

    def get_org_settings(self, **kwargs) -> Response:
        """Get the org's settings"""
        req_user = kwargs['req_user']
        req_user.log(
            operation=Operations.GET,
            resource=Resources.ORG_SETTINGS
        )
        return self.ok(self.settings_service.get_org_settings(req_user.org_id).as_dict())

    def update_org_settings(self, **kwargs) -> Response:
        """Update the org's settings"""
        req_user = kwargs['req_user']
        org_setting = self.validate_update_org_settings_request(req_user.org_id, request.get_json())
        self.settings_service.set_org_settings(org_setting)
        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.ORG_SETTINGS,
            resource_id=req_user.org_id
        )
        return self.ok(self.settings_service.get_org_settings(req_user.org_id).as_dict())

    def update_org_subscription_id(self) -> Response:
        """Set the subscription_id for an org"""
        try:
            request_body = request.get_json()
            customer_id = request_body['customer_id']
            subscription_id = request_body['subscription_id']
        except KeyError:
            raise ValidationError("Missing subscription_id or customer_id from request")

        with session_scope() as session:
            org = session.query(Organisation).filter_by(chargebee_customer_id=customer_id).first()
            if org is None:
                raise ValidationError(f"There is no organisation with customer id {customer_id}")
            else:
                org.chargebee_subscription_id = subscription_id
                return self.ok(f"Applied subscription_id {subscription_id} against org {org.id}")

    def lock_organisation(self, customer_id: str) -> Response:
        """Lock an organisation due to a billing issue."""
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

        return self.ok(f"Successfully locked org {org.id}")

    def unlock_organisation(self, customer_id: str) -> Response:
        """Unlock an organisation after the billing issue has been rectified"""
        with session_scope() as session:
            # get the org from the customer id
            org = session.query(Organisation).filter_by(chargebee_customer_id=customer_id).first()
            if org is None:
                raise ValidationError(f"Org with customer_id {customer_id} doesn't exist")
            elif org.locked is None:
                raise ValidationError(f"Org hasn't been locked")
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

        return self.ok(f"Successfully unlocked org {org.id}")

    def get_org(self, **kwargs) -> Response:
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

    def update_org(self, **kwargs) -> Response:
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
