from app.Middleware import handle_exceptions, requires_jwt, authorize

from app import app
from app.Controllers import OrganisationController
from app.Models.Enums import Operations, Resources


@app.route('/org/settings', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.ORG_SETTINGS)
def get_org_settings(**kwargs):
    return OrganisationController.get_org_settings(**kwargs)


@app.route('/org/settings', methods=['PUT'])
@requires_jwt
@handle_exceptions
@authorize(Operations.UPDATE, Resources.ORG_SETTINGS)
def update_org_settings(**kwargs):
    return OrganisationController.update_org_settings(**kwargs)


@app.route('/org', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.ORGANISATION)
def get_org(**kwargs):
    return OrganisationController.get_org(**kwargs)


@app.route('/org', methods=['PUT'])
@requires_jwt
@handle_exceptions
@authorize(Operations.UPDATE, Resources.ORGANISATION)
def update_org(**kwargs):
    return OrganisationController.update_org(**kwargs)
