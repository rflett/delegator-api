from flask import current_app
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models.Enums import Operations, Resources
from app.Models.RBAC import Permission

api = Namespace(path="/user/pages", name="User", description="Manage a user")


@api.route("/")
class UserPagesController(RequestValidationController):
    @requires_jwt
    @authorize(Operations.GET, Resources.PAGES)
    @api.response(200, "Success", fields.List(fields.String()))
    def get(self, **kwargs):
        """Returns the pages a user can access """
        req_user = kwargs["req_user"]

        # query for permissions that have the resource id like %_PAGE
        with session_scope() as session:
            pages_qry = (
                session.query(Permission.resource_id)
                .filter(Permission.role_id == req_user.role, Permission.resource_id.like("%_PAGE"))
                .all()
            )

            pages = []
            for permission in pages_qry:
                for page in permission:
                    # strip _PAGE
                    pages.append(page.split("_PAGE")[0])

            req_user.log(Operations.GET, Resources.PAGES)
            current_app.logger.info(f"found {len(pages)} pages.")
            return sorted(pages), 200
