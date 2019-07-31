import _thread
import json
import typing

from flask import request, Response

from app import logger, g_response, notification_tokens_table, app_notifications_sns_topic


def do_push(message_body: dict, user_ids: typing.List[int]) -> None:
    """ Publishes the notification to SNS """
    app_notifications_sns_topic.publish(
        TopicArn=app_notifications_sns_topic.arn,
        Message=json.dumps({
            'default': json.dumps({
                "message_body": message_body,
                "user_ids": user_ids
            })
        }),
        MessageStructure='json'
    )


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

    @staticmethod
    def deregister_token(req: request) -> Response:
        """ Deregister a notification token for a notification service """
        from app.Controllers import ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        token_type = ValidationController.validate_deregister_token_request(req.get_json())

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
        return g_response(status=204)

    @staticmethod
    def push(message_body: dict, user_ids: typing.List[int]) -> None:
        """ Publish the message to SNS for pushing to the user """
        _thread.start_new_thread(do_push, (message_body, user_ids))
