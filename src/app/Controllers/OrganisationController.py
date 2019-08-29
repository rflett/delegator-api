import datetime
import typing

from flask import request, Response

from sqlalchemy import exists, func

from app import session_scope, logger, g_response, j_response
from app.Exceptions import ValidationError
from app.Models import Organisation
from app.Models.Enums import Operations, Resources


class OrganisationController(object):
    @staticmethod
    def org_exists(org_identifier: typing.Union[str, int]) -> bool:
        """Checks to see if an organisation exists

        :param org_identifier:  The org_id or name
        :return:                True if the org exists or False
        """
        with session_scope() as session:
            if isinstance(org_identifier, str):
                logger.debug("org_identifier is a str so finding org by name")
                return session.query(exists().where(
                    func.lower(Organisation.name) == func.lower(org_identifier)
                )).scalar()
            elif isinstance(org_identifier, int):
                logger.debug("org_identifier is an int so finding org by id")
                return session.query(exists().where(Organisation.id == org_identifier)).scalar()
            else:
                raise ValueError(f"Bad org_identifier, expected Union[str, int] got {type(org_identifier)}")

    @staticmethod
    def get_org_settings(req: request) -> Response:
        """Get the org's settings

        :param req: The HTTP request
        :return:    HTTP 200 response
        """
        from app.Controllers import AuthorizationController, SettingsController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.ORG_SETTINGS
        )

        req_user.log(
            operation=Operations.GET,
            resource=Resources.ORG_SETTINGS
        )

        return j_response(SettingsController.get_org_settings(req_user.org_id).as_dict())

    @staticmethod
    def update_org_settings(req: request) -> Response:
        """Update the org's settings

        :param req: The HTTP request
        :return:    HTTP 204 response
        """
        from app.Controllers import AuthorizationController, SettingsController, AuthenticationController, \
            ValidationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.UPDATE,
            resource=Resources.ORG_SETTINGS
        )

        org_setting = ValidationController.validate_update_org_settings_request(req_user.org_id, req.get_json())

        SettingsController.set_org_settings(org_setting)

        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.ORG_SETTINGS,
            resource_id=req_user.org_id
        )

        return g_response(status=204)

    @staticmethod
    def update_subscription_info(req: request) -> Response:
        """Set the subscription_id for an org"""
        from app.Controllers import UserController
        try:
            request_body = req.get_json()
            email = request_body['email']
            customer_id = request_body['customer_id']
        except KeyError:
            raise ValidationError("Missing email or customer_id from request")

        with session_scope():
            try:
                org = UserController.get_user_by_email(email).orgs
                org.chargebee_customer_id = customer_id
                return j_response()
            except ValueError:
                raise ValidationError("Email doesn't exist.")

    @staticmethod
    def lock_organisation(customer_id: str, req: request) -> Response:
        """Lock an organisation due to a billing issue."""
        locked_reason = req.get_json().get('locked_reason')
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

        return j_response()

    @staticmethod
    def unlock_organisation(customer_id: str) -> Response:
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

        return j_response()
