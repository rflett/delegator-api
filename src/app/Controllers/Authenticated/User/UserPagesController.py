from flask_restplus import Namespace, fields

from app import session_scope, subscription_api, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models.Enums import Operations, Resources
from app.Models.RBAC import Permission
from app.Models.Response import message_response_dto

user_pages_route = Namespace(
    path="/user/pages",
    name="User Pages",
    description="Used to retrieve information on what a user should be able to access"
)


@user_pages_route.route("/")
class UserPagesController(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.PAGES)
    @user_pages_route.response(200, "Retrieved the authorized pages", [fields.String])
    @user_pages_route.response(400, "Failed to get the user's pages", message_response_dto)
    def get(self, **kwargs):
        """Returns the pages a user can access """
        req_user = kwargs['req_user']

        # query for permissions that have the resource id like %_PAGE
        with session_scope() as session:
            pages_qry = session.query(Permission.resource_id).filter(
                Permission.role_id == req_user.role,
                Permission.resource_id.like("%_PAGE")
            ).all()

            pages = []
            for permission in pages_qry:
                for page in permission:
                    # strip _PAGE
                    pages.append(page.split('_PAGE')[0])

            # Remove reports if user hasn't paid for them
            if not subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('view_reports_page', False):
                pages.remove('REPORTS')

            req_user.log(
                operation=Operations.GET,
                resource=Resources.PAGES
            )
            logger.info(f"found {len(pages)} pages.")
            return self.ok(sorted(pages))
