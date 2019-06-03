from app import app, logger, g_response, session_scope
from app.Controllers import UserController, OrganisationController, ValidationController
from app.Models.RBAC import Operation, Resource
from flask import request, Response


class SignupController(object):
    @staticmethod
    def signup(req: request) -> Response:
        """
        Signup a user, which effectively creates an organisation and a user against that organisation.
        :param req: The request object
        :return:        Response
        """
        request_body = req.get_json()
        # check if org already exists
        if OrganisationController.org_exists(request_body.get('org_name')):
            logger.info(f"organisation {request_body.get('org_name')} already exists")
            return g_response("Organisation already exists.", 400)

        # check if user already exists
        if UserController.user_exists(request_body.get('email')):
            logger.info(f"user {request_body.get('email')} already exists")
            return g_response("User already exists.", 400)

        # validate org
        valid_org = ValidationController.validate_create_org_request(request_body)
        if isinstance(valid_org, Response):
            return valid_org

        # validate user
        valid_user = ValidationController.validate_create_signup_user(request_body)
        if isinstance(valid_user, Response):
            return valid_user

        try:
            create_org_res = OrganisationController.create_org(org_name=valid_org)
        except Exception as e:
            logger.error(str(e))
            return g_response("There was an issue creating the organisation", 500)

        if create_org_res.status_code != 201:
            return create_org_res

        new_org = OrganisationController.get_org_by_name(request_body.get('org_name'))

        try:
            create_user_res = UserController.create_signup_user(org_id=new_org.id, valid_user=valid_user)
        except Exception as e:
            logger.error(str(e))
            # the org was actually created, but the user failed, so delete the org
            if create_org_res.status_code == 201:
                with session_scope() as session:
                    from app.Models import TaskType
                    session.query(TaskType).filter(TaskType.org_id == new_org.id).delete()
                    session.delete(new_org)
                    logger.info(f"deleted the new organisation {new_org.name} "
                                f"since there was an issue creating the user")
            return g_response("There was an issue creating the user", 500)

        if create_user_res.status_code != 201:
            return create_user_res

        return g_response("Successfully signed up.", 200)
