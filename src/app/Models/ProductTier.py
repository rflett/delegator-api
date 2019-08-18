from app import db


class ProductTier(db.Model):
    __tablename__ = "product_tiers"

    plan_id = db.Column('plan_id', db.String, primary_key=True)
    name = db.Column('name', db.String)
    max_users = db.Column('max_users', db.Integer)
    task_activity_log_history = db.Column('task_activity_log_history', db.Integer)
    searchable_dashboard = db.Column('searchable_dashboard', db.Boolean)
    view_user_activity = db.Column('view_user_activity', db.Boolean)
    view_reports_page = db.Column('view_reports_page', db.Boolean)

    def __init__(
        self,
        name: str,
        max_users: int,
        task_activity_log_history: int,  # days
        searchable_dashboard: bool,
        view_user_activity: bool,
        view_reports_page: bool
    ):
        self.name = name
        self.max_users = max_users
        self.task_activity_log_history = task_activity_log_history
        self.searchable_dashboard = searchable_dashboard
        self.view_user_activity = view_user_activity
        self.view_reports_page = view_reports_page

    def as_dict(self) -> dict:
        """
        :return: dict repr of a ProductTier object
        """
        return {
            "id": self.id,
            "name": self.name,
            "max_users": self.max_users,
            "task_activity_log_history": self.task_activity_log_history,
            "searchable_dashboard": self.searchable_dashboard,
            "view_user_activity": self.view_user_activity,
            "view_reports_page": self.view_reports_page
        }
