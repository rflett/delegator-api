import json
import random
import string

from flask import request

from app import logger, session_scope
from app.Controllers.Base import RequestValidationController


class AuthorizationController(RequestValidationController):
    def reset_password(self):
        from app.Controllers import UserController
        request_body = request.get_json()
        self.validate_email(request_body.get('email'))

        with session_scope():
            logger.info(f"received password reset for {request_body.get('email')}")
            user = UserController.get_user_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            logger.info(json.dumps(user.as_dict()))
            logger.info(f"password successfully reset for {request_body.get('email')}")
            return self.ok(f"Password reset successfully, new password is {new_password}")
