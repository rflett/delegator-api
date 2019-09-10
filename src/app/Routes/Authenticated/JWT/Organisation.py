from app.Middleware import handle_exceptions, requires_jwt

from flask import request

from app import app
from app.Controllers import OrganisationController


@app.route('/org/settings', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_org_settings(**kwargs):
    return OrganisationController.get_org_settings(req=request, **kwargs)


@app.route('/org/settings', methods=['PUT'])
@requires_jwt
@handle_exceptions
def update_org_settings(**kwargs):
    return OrganisationController.update_org_settings(req=request, **kwargs)


@app.route('/org', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_org(**kwargs):
    return OrganisationController.get_org(req=request, **kwargs)


@app.route('/org', methods=['PUT'])
@requires_jwt
@handle_exceptions
def update_org(**kwargs):
    return OrganisationController.update_org(req=request, **kwargs)
