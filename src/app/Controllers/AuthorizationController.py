import json
import random
import string

from flask import request

from app import logger, g_response, session_scope
from app.Controllers import ValidationController


class AuthorizationController(object):
    @staticmethod
    def reset_password():
        """ TODO remove and make it an email based reset. """
        from app.Controllers import UserController
        request_body = request.get_json()
        ValidationController.validate_email(request_body.get('email'))

        with session_scope():
            logger.info(f"received password reset for {request_body.get('email')}")
            user = UserController.get_user_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            logger.info(json.dumps(user.as_dict()))
            logger.info(f"password successfully reset for {request_body.get('email')}")
            return g_response(f"Password reset successfully, new password is {new_password}")
