from app import logger, subscription_api


class Subscription(object):

    def __init__(self, subscription_id: str):
        self._subscription_id = subscription_id

        sub_request = subscription_api.get_subscription_meta(self._subscription_id)

        self._status = sub_request['status']
        self._metadata = sub_request['meta_data']
        self._unusable_statuses = ['future', 'paused', 'cancelled']
        self._usable_statuses = ['active', 'non_renewing']

    def max_users(self) -> int:
        """The maximum users that can be created on this plan"""
        if self._status == "trial":
            return -1
        if self._status in self._unusable_statuses:
            return 0
        if self._status in self._usable_statuses:
            ret = self._metadata.get('max_users')
            if ret is None:
                logger.warning(f"Missing max_users metadata for {self._subscription_id}")
                return -1
            else:
                return ret

    def can_get_reports(self) -> bool:
        """Can the subscription get reports?"""
        if self._status == "trial":
            return True
        if self._status in self._unusable_statuses:
            return False
        if self._status in self._usable_statuses:
            ret = self._metadata.get('view_reports_page')
            if ret is None:
                logger.warning(f"Missing view_reports_page metadata for {self._subscription_id}")
                return True
            else:
                return ret

    def task_activity_log_history(self) -> int:
        """The amount of days of task activity log that can be viewed"""
        if self._status == "trial":
            return -1
        if self._status in self._unusable_statuses:
            return 0
        if self._status in self._usable_statuses:
            ret = self._metadata.get('task_activity_log_history')
            if ret is None:
                logger.warning(f"Missing task_activity_log_history metadata for {self._subscription_id}")
                return -1
            else:
                return ret

    def can_search_dashboard(self) -> bool:
        """Can the subscription search the dashboard"""
        if self._status == "trial":
            return True
        if self._status in self._unusable_statuses:
            return False
        if self._status in self._usable_statuses:
            ret = self._metadata.get('searchable_dashboard')
            if ret is None:
                logger.warning(f"Missing searchable_dashboard metadata for {self._subscription_id}")
                return True
            else:
                return ret

    def can_view_user_activity(self) -> bool:
        """Can the subscription view user activity logs"""
        if self._status == "trial":
            return True
        if self._status in self._unusable_statuses:
            return False
        if self._status in self._usable_statuses:
            ret = self._metadata.get('view_user_activity')
            if ret is None:
                logger.warning(f"Missing view_user_activity metadata for {self._subscription_id}")
                return True
            else:
                return ret
