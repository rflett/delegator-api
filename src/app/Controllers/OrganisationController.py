import typing
from app import session_scope, logger, g_response
from app.Controllers import AuthController
from app.Models import Organisation, User
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists


def _org_exists(org_identifier: typing.Union[int, str]) -> bool:
    """
    Checks to see if an org exists
    :param org_identifier:  The org id or name
    :return:                True if the org exists or False
    """
    if isinstance(org_identifier, str):
        logger.debug("org_identifier is a str so finding org by name")
        with session_scope() as session:
            ret = session.query(exists().where(Organisation.name == org_identifier)).scalar()
            return ret
    elif isinstance(org_identifier, int):
        logger.debug("org_identifier is an int so finding org by id")
        with session_scope() as session:
            ret = session.query(exists().where(Organisation.id == org_identifier)).scalar()
            return ret


class OrganisationController(object):
    @staticmethod
    def org_exists(org_identifier: typing.Union[str, int]) -> bool:
        """
        Checks to see if an org exists. Public wrapper function for _org_exists.
        :param org_identifier:  The org id or name
        :return:                True if the org exists or False
        """
        return _org_exists(org_identifier)

    @staticmethod
    def get_org_by_id(id: int) -> Organisation:
        """
        Gets an organisation by its id.
        :param id:  The id of the organisation
        :return:    The Organisation object.
        """
        # TODO this query causes the 'idle in transaction' issue
        if _org_exists(id):
            with session_scope() as session:
                ret = session.query(Organisation).filter(Organisation.id == id).first()
                return ret
        else:
            logger.debug(f"org {id} does not exist")
            raise ValueError(f"Org with id {id} does not exist.")

    @staticmethod
    def get_org_by_name(name: str) -> Organisation:
        """
        Gets an organisation by its name.
        :param name:    The name of the organisation
        :return:        The Organisation object.
        """
        if _org_exists(name):
            with session_scope() as session:
                ret = session.query(Organisation).filter(Organisation.name == name).first()
                return ret
        else:
            logger.debug(f"org {name} does not exist")
            raise ValueError(f"Org with name {name} does not exist.")

    @staticmethod
    def org_create(request: request, require_auth: bool = True) -> Response:
        """
        Creates an organisation.
        :param request:         The request to create an org
        :param require_auth:    If request needs to have authoriziation (e.g. not if signing up)
        :return:                A response
        """

        def create_org(valid_org: Organisation, req_user: User = None) -> Response:
            """
            Creates the organisation
            :param valid_org:  The validated organisation object
            :param req_user:   The user making the request
            :return:           Response
            """
            with session_scope() as session:
                organisation = Organisation(
                    name=valid_org.org_name
                )
                session.add(organisation)
                if isinstance(req_user, User):
                    req_user.log(
                        operation=Operation.CREATE,
                        resource=Resource.ORGANISATION,
                        resource_id=organisation.id
                    )
                logger.debug(f"created organisation {organisation.as_dict()}")
                return g_response("Successfully created the organisation", 201)

        request_body = request.get_json()

        # validate org
        from app.Controllers import ValidationController
        valid_org = ValidationController.validate_create_org_request(request_body)

        if isinstance(valid_org, Response):
            return valid_org

        if require_auth:
            logger.debug("requiring auth to create org")
            req_user = AuthController.authorize_request(
                request=request,
                operation=Operation.CREATE,
                resource=Resource.ORGANISATION,
                resource_org_id=valid_org.org_id
            )
            if isinstance(req_user, Response):
                return req_user
            elif isinstance(req_user, User):
                return create_org(request_body, req_user=req_user)
        else:
            logger.debug("not requiring auth to create org")
            return create_org(valid_org)
