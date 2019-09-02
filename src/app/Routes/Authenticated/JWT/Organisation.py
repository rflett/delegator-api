from app.Middleware import handle_exceptions, requires_jwt

from flask import request

from app import app
from app.Controllers import OrganisationController


@app.route('/org/settings', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_org_settings():
    return OrganisationController.get_org_settings(request)


@app.route('/org/settings', methods=['PUT'])
@requires_jwt
@handle_exceptions
def update_org_settings():
    return OrganisationController.update_org_settings(request)
