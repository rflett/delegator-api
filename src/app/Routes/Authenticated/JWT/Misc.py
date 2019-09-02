from app.Middleware import handle_exceptions, requires_jwt

from flask import request

from app import app
from app.Controllers import AuthenticationController, RoleController, ReportController


@app.route('/logout', methods=['POST'])
@requires_jwt
@handle_exceptions
def logout():
    return AuthenticationController.logout(request.headers)


@app.route('/roles', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_roles():
    return RoleController.get_roles(request)


@app.route('/reporting/all', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_all_reports():
    return ReportController.get_all(request)


