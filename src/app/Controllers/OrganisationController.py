import typing

from flask import request, Response
from sqlalchemy import exists, func

from app import session_scope, logger, g_response, j_response
from app.Exceptions import AuthenticationError, AuthorizationError
from app.Models import Organisation, TaskType
from app.Models.RBAC import Operation, Resource


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
    def create_org(org_name: str) -> Organisation:
        with session_scope() as session:
            organisation = Organisation(
                name=org_name
            )
            session.add(organisation)

        with session_scope() as session:
            session.add(TaskType(label='Other', org_id=organisation.id))

        # create org settings
        organisation.create_settings()

        logger.info(f"created organisation {organisation.as_dict()}")
        return organisation

    @staticmethod
    def get_org_settings(req: request) -> Response:
        """ Returns the org's settings """
        from app.Controllers import AuthorizationController, SettingsController, AuthenticationController
        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.GET,
                resource=Resource.ORG_SETTINGS
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        req_user.log(
            operation=Operation.GET,
            resource=Resource.ORG_SETTINGS
        )
        logger.info(f"user {req_user.id} got settings for org {req_user.org_id}")
        return j_response(SettingsController.get_org_settings(req_user.org_id).as_dict())

    @staticmethod
    def update_org_settings(req: request) -> Response:
        """ Returns the org's settings """
        from app.Controllers import AuthorizationController, SettingsController, AuthenticationController, \
            ValidationController

        try:
            req_user = AuthenticationController.get_user_from_request(req.headers)
        except AuthenticationError as e:
            return g_response(str(e), 400)

        try:
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operation.UPDATE,
                resource=Resource.ORG_SETTINGS
            )
        except AuthorizationError as e:
            return g_response(str(e), 400)

        org_setting = ValidationController.validate_update_org_settings_request(req_user.org_id, req.get_json())

        SettingsController.set_org_settings(org_setting)
        req_user.log(
            operation=Operation.UPDATE,
            resource=Resource.ORG_SETTINGS,
            resource_id=req_user.org_id
        )
        logger.info(f"user {req_user.id} updated settings for org {req_user.org_id}")
        return g_response(status=204)
