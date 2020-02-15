from os import getenv

import requests
from flask import current_app

from app.Extensions.Errors import InternalServerError


class Subscription(object):
    def __init__(self, subscription_id: str):
        self._subscription_id = subscription_id

        subscription_meta = self._get_subscription_meta(subscription_id)

        self._status = subscription_meta["status"]
        self._metadata = subscription_meta["meta_data"]
        self._unusable_statuses = ["future", "paused", "cancelled"]
        self._usable_statuses = ["active", "non_renewing"]

    def task_activity_log_history(self) -> int:
        """The amount of days of task activity log that can be viewed"""
        if self._status == "in_trial":
            return -1
        if self._status in self._unusable_statuses:
            return 0
        if self._status in self._usable_statuses:
            ret = self._metadata.get("task_activity_log_history")
            if ret is None:
                current_app.logger.warning(f"Missing task_activity_log_history metadata for {self._subscription_id}")
                return -1
            else:
                return ret

    def user_activity_log_history(self) -> bool:
        """Can the subscription view user activity logs"""
        if self._status == "in_trial":
            return True
        if self._status in self._unusable_statuses:
            return False
        if self._status in self._usable_statuses:
            ret = self._metadata.get("view_user_activity")
            if ret is None:
                current_app.logger.warning(f"Missing view_user_activity metadata for {self._subscription_id}")
                return True
            else:
                return ret

    def _get_subscription_meta(self, subscription_id) -> dict:
        if getenv("MOCK_SERVICES"):
            return {"status": "in_trial", "meta_data": {}}
        try:
            r = requests.get(
                url=f"{self.url}/subscription/{subscription_id}/quantity",
                headers={"Authorization": f"Bearer {self.create_sa_token()}"},
                timeout=10,
            )
            if r.status_code != 200:
                current_app.logger.error(f"There was an error getting the subscription quantity for {subscription_id}")
                raise InternalServerError("Something went wrong getting details about your subscription!")
            else:
                return r.json()

        except requests.exceptions.RequestException:
            current_app.logger.error(f"There was an error getting the subscription quantity for {subscription_id}")
            raise InternalServerError("Something went wrong getting details about your subscription!")
