from flask import Response, request
from flask_restplus import Namespace

from app import logger, notification_tokens_table
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions
from app.Models.Request import register_notification_token_dto, deregister_notification_token_dto
from app.Models.Response import message_response_dto

notification_token_route = Namespace(
    path="/notification_token",
    name="Notification Tokens",
    description="Notification token registration/de-registration"
)


@notification_token_route.route("/")
class NotificationToken(RequestValidationController):
    @requires_jwt
    @handle_exceptions
    @notification_token_route.expect(register_notification_token_dto)
    @notification_token_route.response(204, "Registration Successful")
    @notification_token_route.response(400, "Registration Failed", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Register a notification token for a notification service"""
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

    @requires_jwt
    @handle_exceptions
    @notification_token_route.expect(deregister_notification_token_dto)
    @notification_token_route.response(204, "De-registration Successful")
    @notification_token_route.response(400, "De-registration Failed", message_response_dto)
    def delete(self, **kwargs) -> Response:
        """De-register a notification token for a notification service"""
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

        logger.info(f"De-registered token for user: {req_user.id}, token_type: {token_type}.")
        return self.no_content()
