from flask import request, Response

from app import logger, g_response, session_scope
from app.Controllers import OrganisationController


class SignupController(object):
    @staticmethod
    def signup(req: request) -> Response:
        """
        Signup a user, which effectively creates an organisation and a user against that organisation.
        :param req: The request object
        :return:        Response
        """
        from app.Controllers import ValidationController, UserController

        request_body = req.get_json()

        # validate org
        org_name = ValidationController.validate_create_org_request(request_body)
        if isinstance(org_name, Response):
            return org_name

        # validate user
        valid_user = ValidationController.validate_create_signup_user(request_body)
        if isinstance(valid_user, Response):
            return valid_user

        try:
            new_org = OrganisationController.create_org(org_name=org_name)
        except Exception as e:
            logger.error(str(e))
            return g_response("There was an issue creating the organisation", 500)

        try:
            UserController.create_signup_user(org_id=new_org.id, valid_user=valid_user)
            return g_response("Successfully signed up.", 200)
        except Exception as e:
            logger.error(str(e))
            # the org was actually created, but the user failed, so delete the org and default task type
            if new_org.status_code == 201:
                with session_scope() as session:
                    from app.Models import TaskType
                    session.query(TaskType).filter(TaskType.org_id == new_org.id).delete()
                    session.delete(new_org)
                    logger.info(f"deleted the new organisation {new_org.name} "
                                f"since there was an issue creating the user")
            return g_response("There was an issue creating the user", 500)
