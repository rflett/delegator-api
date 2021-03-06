from flask_restx import Namespace, fields
from sqlalchemy import and_

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models.Enums import Operations, Resources, Roles
from app.Models.RBAC import Role

api = Namespace(path="/roles", name="Roles", description="Manage roles")


role_dto = api.model(
    "Role",
    {
        "id": fields.String(),
        "rank": fields.Integer(min=0, max=2),
        "name": fields.String(enum=Roles.all),
        "description": fields.String(),
        "disabled": fields.Boolean(),
        "tooltip": fields.String(),
    },
)

roles_response = api.model("Roles Response", {"roles": fields.List(fields.Nested(role_dto))})


@api.route("/")
class Roles(RequestValidationController):
    @requires_jwt
    @authorize(Operations.GET, Resources.ROLES)
    @api.marshal_with(roles_response, code=200)
    @api.response(200, "Roles Retrieved", roles_response)
    def get(self, **kwargs):
        """Return all roles lower in rank than the requesting user's role."""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            # rank > 50 are reserved for admin duties
            roles_qry = session.query(Role).filter(and_(Role.rank <= 50)).all()

        # the role will be disabled if its rank is higher than the users rank
        roles = [r.as_dict(disabled=r.rank < req_user.roles.rank) for r in roles_qry]

        req_user.log(Operations.GET, Resources.ROLES)
        return {"roles": roles}, 200
