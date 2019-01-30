from app import DBSession
from app.Controllers import ValidationController, UserController, OrganisationController
from app.Models import Organisation, User
from app.Models.RBAC import Operation, Resource
from flask import request, Response

session = DBSession()

SIGNUP_ROLE = 'ADMIN'


class SignupController(object):
    @staticmethod
    def signup(request: request) -> Response:
        """
        Signup a user, which effectively creates an organisation and a user against that organisation.
        :param request:
        :return:
        """
        request_body = request.get_json()

        # validate and create organisation
        check_org = ValidationController.validate_org_request(request_body)
        if isinstance(check_org, Response):
            return check_org
        else:
            organisation = Organisation(
                name=check_org.org_name
            )
            session.add(organisation)
            session.commit()

            # validate and check user
            new_org = OrganisationController.get_org_by_name(organisation.name)
            request_body['role_name'] = SIGNUP_ROLE
            request_body['org_id'] = new_org.id
            check_user = ValidationController.validate_user_request(request_body)
            if isinstance(check_user, Response):
                return check_user
            else:
                user = User(
                    org_id=check_user.org_id,
                    email=check_user.email,
                    first_name=check_user.first_name,
                    last_name=check_user.last_name,
                    password=check_user.password,
                    role=check_user.role_name
                )
                session.add(user)
                session.commit()

                # log events
                new_user = UserController.get_user_by_email(user.email)
                new_user.log(Operation.CREATE, Resource.ORGANISATION)
                new_user.log(Operation.CREATE, Resource.USER)

                return Response("Successfully signed up.", 200)
