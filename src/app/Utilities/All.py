import typing

from sqlalchemy import and_

from app.Extensions.Database import session_scope
from app.Models.Dao import Task
from app.Extensions.Errors import ResourceNotFoundError


def get_task_by_id(task_id: int, org_id: int) -> Task:
    """Get a Task from the database from its id
    :param task_id: The ID of the task
    :param org_id: The org ID that the task should be in
    :return: A task
    """
    from app.Models.Dao import Task

    with session_scope() as session:
        task = session.query(Task).filter_by(id=task_id, org_id=org_id).first()
        if task is None:
            raise ResourceNotFoundError("Task does not exist")
        else:
            return task


def get_all_user_ids(org_id: int, exclude: list = None) -> typing.List[int]:
    """Return a list of all user IDs within in an org

    :param org_id: The ID of the org to return users from
    :param exclude: An optional list of user IDs to exclude from the return list
    :return: A list of user IDs
    """
    from app.Models.Dao import User

    if exclude is None:
        exclude = []

    with session_scope() as session:
        user_ids_qry = session.query(User.id).filter(and_(User.org_id == org_id, User.id.notin_(exclude)))

    return [user_id[0] for user_id in user_ids_qry]


def reindex_display_orders(org_id: int, new_position: int = None):
    """Re-index's all task display orders for an organisation. If a position is provided then
    only tasks above it will be re-indexed. This should be called whenever its visual position in the UI is updated

    :param org_id: The ID of the org in which to re-index that tasks
    :param new_position: An optional position from which to re-index tasks from
    :return: None
    """
    with session_scope() as session:
        if new_position is None:
            session.execute(
                """
                   UPDATE tasks
                   SET display_order = display_order + 1
                   WHERE org_id = :org_id
                """,
                {"org_id": org_id},
            )
        else:
            session.execute(
                """
                   UPDATE tasks
                   SET display_order = display_order + 1
                   WHERE org_id = :org_id
                   AND display_order >= :new_position
                """,
                {"org_id": org_id, "new_position": new_position},
            )
