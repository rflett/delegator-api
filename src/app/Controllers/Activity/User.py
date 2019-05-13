from app import logger, user_activity_table


class UserActivity(object):
    @staticmethod
    def get_activity(user_id: int) -> dict:
        """ Return user activity from DynamoDB """
        return {
            "2019-05-13 19:39:00": f"User {user_id} made the user activity endpoint"
        }
