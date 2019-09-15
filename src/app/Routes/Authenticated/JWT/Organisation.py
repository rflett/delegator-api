from app.Decorators import handle_exceptions, requires_jwt, authorize

from app import app
from app.Controllers.Authenticated import Organisation
from app.Models.Enums import Operations, Resources


@app.route('/org/settings', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.ORG_SETTINGS)
def get_org_settings(**kwargs):
    return Organisation.get_org_settings(**kwargs)


@app.route('/org/settings', methods=['PUT'])
@requires_jwt
@handle_exceptions
@authorize(Operations.UPDATE, Resources.ORG_SETTINGS)
def update_org_settings(**kwargs):
    return Organisation.update_org_settings(**kwargs)


@app.route('/org', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.ORGANISATION)
def get_org(**kwargs):
    return Organisation.get_org(**kwargs)


@app.route('/org', methods=['PUT'])
@requires_jwt
@handle_exceptions
@authorize(Operations.UPDATE, Resources.ORGANISATION)
def update_org(**kwargs):
    return Organisation.update_org(**kwargs)
