import datetime

from app import session_scope
from app.Models import ActiveUser, User


class ActiveUserService(object):
    @staticmethod
    def user_is_active(user: User) -> None:
        """Marks a user as active if they are not active already. If they're already active then update them."""
        with session_scope() as session:
            already_active = session.query(ActiveUser).filter_by(user_id=user.id).first()
            if already_active is None:
                # user is not active, so create
                active_user = ActiveUser(
                    user_id=user.id,
                    org_id=user.org_id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    last_active=datetime.datetime.utcnow()
                )
                session.add(active_user)
            else:
                # user is active, so update
                already_active.last_active = datetime.datetime.utcnow()

    @staticmethod
    def user_is_inactive(user: User) -> None:
        """Mark user as inactive by deleting their record in the active users table"""
        with session_scope() as session:
            session.query(ActiveUser).filter_by(user_id=user.id).delete()