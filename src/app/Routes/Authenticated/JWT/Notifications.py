from app.Decorators import handle_exceptions, requires_jwt

from app import app
from app.Controllers.Authenticated import NotificationToken


@app.route('/notification_token', methods=['POST'])
@requires_jwt
@handle_exceptions
def register_token(**kwargs):
    return NotificationToken.register_token(**kwargs)


@app.route('/notification_token', methods=['DELETE'])
@requires_jwt
@handle_exceptions
def deregister_token(**kwargs):
    return NotificationToken.deregister_token(**kwargs)
