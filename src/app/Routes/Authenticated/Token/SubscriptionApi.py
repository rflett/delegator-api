from app.Decorators import handle_exceptions, requires_token_auth

from app import app
from app.Controllers import TaskController
from app.Controllers.Authenticated import Organisation


@app.route('/org/lock/<customer_id>', methods=['PUT'])
@requires_token_auth
@handle_exceptions
def lock_organisation(customer_id):
    return Organisation.lock_organisation(customer_id)


@app.route('/org/lock/<customer_id>', methods=['DELETE'])
@requires_token_auth
@handle_exceptions
def unlock_organisation(customer_id):
    return Organisation.unlock_organisation(customer_id)


@app.route('/org/subscription', methods=['POST'])
@requires_token_auth
@handle_exceptions
def update_org_subscription_id():
    return Organisation.update_org_subscription_id()


@app.route('/task/priority', methods=['PUT'])
@requires_token_auth
@handle_exceptions
def change_priority():
    return TaskController.change_priority()
