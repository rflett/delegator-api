from app.Middleware import handle_exceptions, requires_jwt

from flask import request

from app import app
from app.Controllers import NotificationController


@app.route('/notification_token', methods=['POST'])
@requires_jwt
@handle_exceptions
def register_token():
    return NotificationController.register_token(request)


@app.route('/notification_token', methods=['DELETE'])
@requires_jwt
@handle_exceptions
def deregister_token():
    return NotificationController.deregister_token(request)
