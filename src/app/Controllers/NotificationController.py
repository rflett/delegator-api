import _thread
import json
import typing
from os import getenv

from flask import Response, request

from app import logger, notification_tokens_table, app_notifications_sqs
from app.Controllers.Base import RequestValidationController


class NotificationController(RequestValidationController):

    @staticmethod
    def _do_push(msg: str, user_ids: typing.Union[int, typing.List[int]]) -> None:
        """ Publishes the notification to SNS """
        if isinstance(user_ids, int):
            user_ids = [user_ids]

        if getenv('APP_ENV', 'Local') == 'Local':
            logger.info(f"WOULD have pushed notification to SQS for {len(user_ids)} users.")
            return None

        app_notifications_sqs.send_message(
            MessageBody=json.dumps({
                "msg": msg,
                "user_ids": user_ids
            })
        )

        logger.info(f"Pushed notification to SQS for {len(user_ids)} users.")

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

    def push(self, msg: str, user_ids: typing.Union[int, typing.List[int]]) -> None:
        """ Publish the message to SNS for pushing to the user """
        _thread.start_new_thread(self._do_push, (msg, user_ids))
