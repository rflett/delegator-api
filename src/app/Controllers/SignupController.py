from flask import request, Response

from app import logger, g_response, session_scope
from app.Models import Organisation


class SignupController(object):
    @staticmethod
    def signup(req: request) -> Response:
        """Signup a user.

        The organisation name and user details are taken, validated, and then created if there are no validation issues.

        :param req: The HTTP request
        :return:    A HTTP 200 or 500 response
        """
        from app.Controllers import ValidationController, UserController
        from app.Models import TaskType

        # get the request body
        request_body = req.get_json()

        # validate org
        org_name, subscription_details = ValidationController.validate_create_org_request(request_body)

        # validate user
        valid_user = ValidationController.validate_create_signup_user(request_body)

        # try and create the org, if there are issues then
        try:
            # create the organisation
            with session_scope() as session:
                organisation = Organisation(
                    name=org_name,
                    product_tier=subscription_details['plan_id'],
                    chargebee_customer_id=subscription_details['customer_id'],
                    chargebee_subscription_id=subscription_details['subscription_id']
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

        try:
            # try and create the user since the org was created successfully
            UserController.create_signup_user(org_id=organisation.id, valid_user=valid_user)
            return g_response("Successfully signed up.", 200)
        except Exception as e:
            logger.error(str(e))
            # the org was actually created, but the user failed, so delete the org and default task type
            with session_scope() as session:
                from app.Models import TaskType
                session.query(TaskType).filter_by(org_id=organisation.id).delete()
                session.delete(organisation)
                logger.info(f"Deleted the new organisation {organisation.name} "
                            f"since there was an issue creating the user.")
            return g_response("There was an issue creating the user.", 500)
