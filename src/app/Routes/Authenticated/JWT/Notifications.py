from app.Decorators import handle_exceptions, requires_jwt

from app import app
from app.Controllers import NotificationController


@app.route('/notification_token', methods=['POST'])
@requires_jwt
@handle_exceptions
def register_token(**kwargs):
    return NotificationController.register_token(**kwargs)


@app.route('/notification_token', methods=['DELETE'])
@requires_jwt
@handle_exceptions
def deregister_token(**kwargs):
    return NotificationController.deregister_token(**kwargs)
