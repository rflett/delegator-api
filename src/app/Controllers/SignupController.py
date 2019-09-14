from flask import request, Response

from app import logger, session_scope, subscription_api
from app.Controllers.Base import RequestValidationController
from app.Models import Organisation, TaskType


class SignupController(RequestValidationController):
    def signup(self) -> Response:
        """Signup a user.

        The organisation name and user details are taken, validated, and then created if there are no validation issues.
        """
        from app.Controllers import UserController

        # get the request body
        request_body = request.get_json()

        # validate org
        org_name = self.validate_create_org_request(request_body)

        # validate user
        valid_user = self.validate_create_signup_user(request_body)

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
            return self.oh_god("There was an issue creating the organisation.")

        # try and create the user since the org was created successfully
        try:
            user = UserController.create_signup_user(org_id=organisation.id, valid_user=valid_user)
        except Exception as e:
            logger.error(str(e))
            # the org was actually created, but the user failed, so delete the org and default task type
            with session_scope() as session:
                session.query(TaskType).filter_by(org_id=organisation.id).delete()
                session.delete(organisation)
                logger.info(f"Deleted the new organisation {organisation.name} "
                            f"since there was an issue creating the user.")
            return self.oh_god("There was an issue creating the user.")

        customer_id, plan_url = subscription_api.create_customer(
            plan_id=request_body.get('plan_id'),
            user_dict=user.as_dict(),
            org_name=organisation.name
        )

        with session_scope():
            organisation.chargebee_customer_id = customer_id

        return self.ok({"url": plan_url})
