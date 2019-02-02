from app import DBSession, app
from app.Controllers import ValidationController, UserController, OrganisationController
from app.Models import Organisation, User
from app.Models.RBAC import Operation, Resource
from flask import request, Response

session = DBSession()


class SignupController(object):
    @staticmethod
    def signup(request: request) -> Response:
        """
        Signup a user, which effectively creates an organisation and a user against that organisation.
        :param request:
        :return:
        """
        request_body = request.get_json()

        try:
            create_org_res = OrganisationController.org_create(request, require_auth=False)
        except Exception as e:
            # rollback org
            session.rollback()
            return Response("There was an issue creating the organisation", 500)

        if create_org_res.status_code != 200:
            return create_org_res

        new_org = OrganisationController.get_org_by_name(request_body.get('org_name'))
        request_body['role_name'] = app.config['SIGNUP_ROLE']
        request_body['org_id'] = new_org.id

        try:
            create_user_res = UserController.user_create(request, require_auth=False)
        except Exception as e:
            # rollback org and user
            session.rollback()
            return Response("There was an issue creating the user", 500)

        if create_user_res.status_code != 200:
            return create_user_res

        # log events
        new_user = UserController.get_user_by_email(request_body.get('email'))
        new_user.log(
            operation=Operation.CREATE,
            resource=Resource.ORGANISATION
        )
        new_user.log(
            operation=Operation.CREATE,
            resource=Resource.USER
        )

        return Response("Successfully signed up.", 200)
