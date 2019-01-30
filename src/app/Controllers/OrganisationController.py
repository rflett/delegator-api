from app import DBSession
from app.Controllers import AuthController, ValidationController
from app.Models import Organisation, User
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists

session = DBSession()


class OrganisationController(object):
    @staticmethod
    def org_exists(org_name: str) -> bool:
        """
        Checks to see if an org exists

        :param org_name str: The org name

        :return: True if the org exists or False
        """
        return session.query(exists().where(Organisation.name == org_name)).scalar()

    @staticmethod
    def get_org_by_id(id: int) -> Organisation:
        """ 
        Gets an organisation by its id.
        
        :param id: The id of the organisation

        :return: The Organisation object.
        """
        return session.query(Organisation).filter(Organisation.id == id).first()

    @staticmethod
    def get_org_by_name(name: str) -> Organisation:
        """
        Gets an organisation by its name.

        :param name: The name of the organisation

        :return: The Organisation object.
        """
        return session.query(Organisation).filter(Organisation.name == name).first()

    @staticmethod
    def org_create(request: request) -> Response:
        """
        Creates an organisation.

        :param request: The request to create an org
        :return: A response
        """
        from app.Controllers import ValidationController
        req_user = AuthController.authorize_request(request, Operation.CREATE, Resource.ORGANISATION)
        if isinstance(req_user, Response):
            return req_user
        elif isinstance(req_user, User):
            # create org
            request_body = request.get_json()
            check_request = ValidationController.validate_org_request(request_body)
            if isinstance(check_request, Response):
                return check_request
            else:
                organisation = Organisation(
                    name=check_request.org_name
                )
                session.add(organisation)
                session.commit()

                req_user.log(Operation.CREATE, Resource.ORGANISATION)

                return Response("Successfully created the organisation", 200)
