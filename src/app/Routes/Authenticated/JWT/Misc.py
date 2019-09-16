from app.Decorators import handle_exceptions, requires_jwt, authorize

from app import app
from app.Controllers import AuthenticationController, RoleController
from app.Controllers.Authenticated import Reporting
from app.Models.Enums import Operations, Resources


@app.route('/logout', methods=['POST'])
@requires_jwt
@handle_exceptions
def logout(**kwargs):
    return AuthenticationController.logout(**kwargs)


@app.route('/roles', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.ROLES)
def get_roles(**kwargs):
    return RoleController.get_roles(**kwargs)


@app.route('/reporting/all', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.REPORTS_PAGE)
def get_all_reports(**kwargs):
    return Reporting.get_all(**kwargs)
