from flask import Response, request

from app import logger, notification_tokens_table
from app.Controllers.Base import RequestValidationController


class NotificationController(RequestValidationController):
    def register_token(self, **kwargs) -> Response:
        """ Register a notification token for a notification service """
        req_user = kwargs['req_user']

        token_type, token = self.validate_register_token_request(request.get_json())

        notification_tokens_table.update_item(
            Key={
                "user_id": req_user.id,
            },
            AttributeUpdates={
                token_type: {
                    'Value': token,
                    'Action': "PUT"
                }
            },
            ReturnValues='NONE'
        )

        logger.info(f"Registered token for user: {req_user.id}, token_type: {token_type}.")
        return self.no_content()

    def deregister_token(self, **kwargs) -> Response:
        """ Deregister a notification token for a notification service """
        req_user = kwargs['req_user']

        token_type = self.validate_deregister_token_request(request.get_json())

        notification_tokens_table.update_item(
            Key={
                "user_id": req_user.id,
            },
            AttributeUpdates={
                token_type: {
                    'Action': "DELETE"
                }
            },
            ReturnValues='NONE'
        )

        logger.info(f"Deregistered token for user: {req_user.id}, token_type: {token_type}.")
        return self.no_content()
