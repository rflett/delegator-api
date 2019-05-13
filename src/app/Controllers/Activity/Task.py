from app import logger, user_activity_table


class TaskActivity(object):
    @staticmethod
    def get_activity(task_id: int) -> dict:
        """ Return user activity from DynamoDB """
        return {
            "2019-05-13 19:39:00": f"Here's a task with id {task_id}"
        }
