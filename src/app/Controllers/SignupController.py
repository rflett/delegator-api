from app import session, app, logger, g_response
from app.Controllers import UserController, OrganisationController
from app.Models.RBAC import Operation, Resource
from flask import request, Response


class SignupController(object):
    @staticmethod
    def signup(request: request) -> Response:
        """
        Signup a user, which effectively creates an organisation and a user against that organisation.
        :param request: The request object
        :return:        Response
        """
        request_body = request.get_json()

        # check if org already exists
        if OrganisationController.org_exists(request_body.get('org_name')):
            logger.debug(f"organisation {request_body.get('org_name')} already exists")
            return g_response("Organisation already exists.", 400)

        # check if user already exists
        if UserController.user_exists(request_body.get('email')):
            logger.debug(f"user {request_body.get('email')} already exists")
            return g_response("User already exists.", 400)

        try:
            create_org_res = OrganisationController.org_create(request, require_auth=False)
        except Exception as e:
            # rollback org
            logger.error(str(e))
            session.rollback()
            return g_response("There was an issue creating the organisation", 500)

        if create_org_res.status_code != 201:
            return create_org_res

        new_org = OrganisationController.get_org_by_name(request_body.get('org_name'))
        request_body['role_name'] = app.config['SIGNUP_ROLE']
        request_body['org_id'] = new_org.id

        try:
            create_user_res = UserController.user_create(request, require_auth=False)
        except Exception as e:
            # rollback org and user
            logger.error(str(e))
            session.rollback()
            return g_response("There was an issue creating the user", 500)

        if create_user_res.status_code != 201:
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

        return g_response("Successfully signed up.", 200)
