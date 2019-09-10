from app.Middleware import handle_exceptions, requires_jwt

from app import app
from app.Controllers import AuthenticationController, RoleController, ReportController


@app.route('/logout', methods=['POST'])
@requires_jwt
@handle_exceptions
def logout(**kwargs):
    return AuthenticationController.logout(**kwargs)


@app.route('/roles', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_roles(**kwargs):
    return RoleController.get_roles(**kwargs)


@app.route('/reporting/all', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_all_reports(**kwargs):
    return ReportController.get_all(**kwargs)
