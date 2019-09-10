from flask import request, Response

from app import logger, g_response, session_scope, j_response, subscription_api
from app.Models import Organisation, TaskType


class SignupController(object):
    @staticmethod
    def signup() -> Response:
        """Signup a user.

        The organisation name and user details are taken, validated, and then created if there are no validation issues.

        :param req: The HTTP request
        :return:    A HTTP 200 or 500 response
        """
        from app.Controllers import ValidationController, UserController

        # get the request body
        request_body = request.get_json()

        # validate org
        org_name = ValidationController.validate_create_org_request(request_body)

        # validate user
        valid_user = ValidationController.validate_create_signup_user(request_body)

        # try and create the org, if there are issues then
        try:
            # create the organisation
            with session_scope() as session:
                organisation = Organisation(
                    name=org_name
                )
                session.add(organisation)

            # add default task type
            with session_scope() as session:
                session.add(TaskType(label='Other', org_id=organisation.id))

            # create org settings
            organisation.create_settings()

        except Exception as e:
            logger.error(str(e))
            return g_response("There was an issue creating the organisation.", 500)

        # try and create the user since the org was created successfully
        try:
            UserController.create_signup_user(org_id=organisation.id, valid_user=valid_user)
        except Exception as e:
            logger.error(str(e))
            # the org was actually created, but the user failed, so delete the org and default task type
            with session_scope() as session:
                session.query(TaskType).filter_by(org_id=organisation.id).delete()
                session.delete(organisation)
                logger.info(f"Deleted the new organisation {organisation.name} "
                            f"since there was an issue creating the user.")
            return g_response("There was an issue creating the user.", 500)

        hosted_page_url = subscription_api.get_hosted_page(
            plan_id=request_body.get('plan_id'),
            user_dict=valid_user
        )

        return j_response({"url": hosted_page_url}, 200)
