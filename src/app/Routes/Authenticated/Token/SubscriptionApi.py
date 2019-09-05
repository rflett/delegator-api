from app.Middleware import handle_exceptions, requires_token_auth

from flask import request

from app import app
from app.Controllers import OrganisationController, TaskController


@app.route('/org/lock/<customer_id>', methods=['PUT'])
@requires_token_auth
@handle_exceptions
def lock_organisation(customer_id):
    return OrganisationController.lock_organisation(customer_id, request)


@app.route('/org/lock/<customer_id>', methods=['DELETE'])
@requires_token_auth
@handle_exceptions
def unlock_organisation(customer_id):
    return OrganisationController.unlock_organisation(customer_id)


@app.route('/org/customer', methods=['POST'])
@requires_token_auth
@handle_exceptions
def update_org_customer_id():
    return OrganisationController.update_org_customer_id(request)


@app.route('/org/subscription', methods=['POST'])
@requires_token_auth
@handle_exceptions
def update_org_subscription_id():
    return OrganisationController.update_org_subscription_id(request)


@app.route('/task/priority', methods=['PUT'])
@requires_token_auth
@handle_exceptions
def change_priority():
    return TaskController.change_priority(request)