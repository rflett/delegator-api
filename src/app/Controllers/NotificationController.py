from flask import request, Response

from app import logger, g_response, notification_tokens_table


class NotificationController(object):
    @staticmethod
    def register_token(req: request) -> Response:
        """ Register a notification token for a notification service """
        from app.Controllers import ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        token_type, token = ValidationController.validate_register_token_request(req.get_json())

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
        return g_response(status=204)
