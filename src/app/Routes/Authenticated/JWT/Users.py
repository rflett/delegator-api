from app.Decorators import handle_exceptions, requires_jwt, authorize

from app import app
from app.Controllers import UserControllerbak
from app.Models.Enums import Operations, Resources


@app.route('/user/<int:user_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.USER)
def get_user(user_id, **kwargs):
    return UserControllerbak.get_user(user_id, **kwargs)


@app.route('/user/<int:user_id>', methods=['DELETE'])
@requires_jwt
@handle_exceptions
@authorize(Operations.DELETE, Resources.USER)
def delete_user(user_id, **kwargs):
    return UserControllerbak.delete_user(user_id, **kwargs)


@app.route('/user/pages', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.PAGES)
def user_pages(**kwargs):
    return UserControllerbak.user_pages(**kwargs)


@app.route('/user/settings', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.USER_SETTINGS)
def get_user_settings(**kwargs):
    return UserControllerbak.get_user_settings(**kwargs)


@app.route('/user/settings', methods=['PUT'])
@requires_jwt
@handle_exceptions
@authorize(Operations.UPDATE, Resources.USER_SETTINGS)
def update_user_settings(**kwargs):
    return UserControllerbak.update_user_settings(**kwargs)


@app.route('/user/activity/<int:user_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.USER_ACTIVITY)
def get_user_activity(user_id, **kwargs):
    return UserControllerbak.get_user_activity(user_id, **kwargs)


@app.route('/users', methods=['POST'])
@requires_jwt
@handle_exceptions
@authorize(Operations.CREATE, Resources.USER)
def create_user(**kwargs):
    return UserControllerbak.create_user(**kwargs)


@app.route('/users', methods=['GET'])
@requires_jwt
@handle_exceptions
@authorize(Operations.GET, Resources.USERS)
def get_users(**kwargs):
    return UserControllerbak.get_users(**kwargs)


@app.route('/users', methods=['PUT'])
@requires_jwt
@handle_exceptions
@authorize(Operations.UPDATE, Resources.USER)
def update_user(**kwargs):
    return UserControllerbak.update_user(**kwargs)
