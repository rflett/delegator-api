import typing

from flask import request, Response
from sqlalchemy import exists, func

from app import session_scope, logger, g_response, j_response
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
    def get_org_by_id(org_id: int) -> Organisation:
        """Gets an organisation by its id.

        :param org_id: The id of the organisation
        """
        with session_scope() as session:
            ret = session.query(Organisation).filter(Organisation.id == org_id).first()
        if ret is None:
            logger.info(f"Org {org_id} does not exist.")
            raise ValueError(f"Org {org_id} does not exist.")
        else:
            return ret

    @staticmethod
    def get_org_by_name(name: str) -> Organisation:
        """Gets an organisation by its name.

        :param name: The name of the organisation
        """
        with session_scope() as session:
            ret = session.query(Organisation).filter(Organisation.name == name).first()
        if ret is None:
            logger.info(f"Org {name} does not exist.")
            raise ValueError(f"Org {name} does not exist.")
        else:
            return ret

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
