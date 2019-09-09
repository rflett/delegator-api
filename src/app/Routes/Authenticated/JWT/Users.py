from app.Middleware import handle_exceptions, requires_jwt

from flask import request

from app import app
from app.Controllers import UserController, ActiveUserController


@app.route('/user/<int:user_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_user(user_id):
    return UserController.get_user(user_id, request)


@app.route('/user/<int:user_id>', methods=['DELETE'])
@requires_jwt
@handle_exceptions
def delete_user(user_id):
    return UserController.delete_user(user_id, request)


@app.route('/user/pages', methods=['GET'])
@requires_jwt
@handle_exceptions
def user_pages():
    return UserController.user_pages(request)


@app.route('/user/settings', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_user_settings():
    return UserController.get_user_settings(request)


@app.route('/user/settings', methods=['PUT'])
@requires_jwt
@handle_exceptions
def update_user_settings():
    return UserController.update_user_settings(request)


@app.route('/user/activity/<int:user_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_user_activity(user_id):
    return UserController.get_user_activity(user_id, request)


@app.route('/users', methods=['POST'])
@requires_jwt
@handle_exceptions
def create_user():
    return UserController.create_user(request)


@app.route('/users', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_users():
    return UserController.get_users(request)


@app.route('/users', methods=['PUT'])
@requires_jwt
@handle_exceptions
def update_user():
    return UserController.update_user(request)


@app.route('/users/active', methods=['GET'])
@requires_jwt
@handle_exceptions
def active_users():
    return ActiveUserController.get_active_users(request)
