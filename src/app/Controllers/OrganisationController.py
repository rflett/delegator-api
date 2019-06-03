import typing
from app import session_scope, logger, g_response, j_response
from app.Models import Organisation, TaskType, OrgSetting
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists, func


class OrganisationController(object):
    @staticmethod
    def org_exists(org_identifier: typing.Union[str, int]) -> bool:
        """
        Checks to see if an org exists. Public wrapper function for _org_exists.
        :param org_identifier:  The org id or name
        :return:                True if the org exists or False
        """
        with session_scope() as session:
            if isinstance(org_identifier, str):
                logger.info("org_identifier is a str so finding org by name")
                ret = session.query(exists().where(
                    func.lower(Organisation.name) == func.lower(org_identifier)
                )).scalar()
            elif isinstance(org_identifier, int):
                logger.info("org_identifier is an int so finding org by id")
                ret = session.query(exists().where(Organisation.id == org_identifier)).scalar()
            else:
                raise ValueError(f"bad org_identifier, expected Union[str, int] got {type(org_identifier)}")

        return ret

    @staticmethod
    def get_org_by_id(id: int) -> Organisation:
        """  Gets an organisation by its id. """
        with session_scope() as session:
            ret = session.query(Organisation).filter(Organisation.id == id).first()
        if ret is None:
            logger.info(f"org {id} does not exist")
            raise ValueError(f"Org with id {id} does not exist.")
        else:
            return ret

    @staticmethod
    def get_org_by_name(name: str) -> Organisation:
        """ Gets an organisation by its name. """
        with session_scope() as session:
            ret = session.query(Organisation).filter(Organisation.name == name).first()
        if ret is None:
            logger.info(f"org {name} does not exist")
            raise ValueError(f"Org with name {name} does not exist.")
        else:
            return ret

    @staticmethod
    def create_org(org_name: str) -> Response:
        from app.Controllers import SettingsController

        with session_scope() as session:
            organisation = Organisation(
                name=org_name
            )
            session.add(organisation)

        with session_scope() as session:
            session.add(TaskType(label='Other', org_id=organisation.id))

        # create org settings
        SettingsController.set_org_settings(OrgSetting(org_id=organisation.id))

        logger.info(f"created organisation {organisation.as_dict()}")
        return g_response("Successfully created the organisation", 201)

    @staticmethod
    def get_org_settings(req: request) -> Response:
        """ Returns the org's settings """
        from app.Controllers import AuthController, SettingsController
        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.ORG_SETTINGS
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        req_user.log(
            operation=Operation.CREATE,
            resource=Resource.ORGANISATION,
            resource_id=req_user.org_id
        )
        logger.info(f"user {req_user.id} got settings for org {req_user.org_id}")
        return j_response(SettingsController.get_org_settings(req_user.org_id).as_dict())

    @staticmethod
    def update_org_settings(req: request) -> Response:
        """ Returns the org's settings """
        from app.Controllers import AuthController, ValidationController, SettingsController

        valid_org_settings = ValidationController.validate_update_org_settings_request(req.get_json())
        # invalid
        if isinstance(valid_org_settings, Response):
            return valid_org_settings

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.UPDATE,
            resource=Resource.ORG_SETTINGS,
            resource_org_id=valid_org_settings.get('org_id')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        SettingsController.set_org_settings(valid_org_settings.get('org_settings'))
        req_user.log(
            operation=Operation.UPDATE,
            resource=Resource.ORG_SETTINGS,
            resource_id=valid_org_settings.get('org_id')
        )
        logger.info(f"user {req_user.id} updated settings for org {req_user.org_id}")
        return g_response(status=204)
