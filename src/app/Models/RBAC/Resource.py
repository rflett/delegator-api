import datetime
from app import db

USER = 'USER'
ORGANISATION = 'ORGANISATION'
TASK = 'TASK'
TASKS = 'TASKS'
ROLE = 'ROLE'
ROLES = 'ROLES'
USERS = 'USERS'
TASK_PRIORITIES = 'TASK_PRIORITIES'
TASK_STATUSES = 'TASK_STATUSES'
TASK_TYPE = 'TASK_TYPE'
TASK_TYPES = 'TASK_TYPES'
ACTIVE_USERS = 'ACTIVE_USERS'
PAGES = 'PAGES'
DASHBOARD_PAGE = 'DASHBOARD_PAGE'
USERS_PAGE = 'USERS_PAGE'
REPORTS_PAGE = 'REPORTS_PAGE'
REPORTS = 'REPORTS'
USER_SETTINGS = 'USER_SETTINGS'
ORG_SETTINGS = 'ORG_SETTINGS'
TASK_TYPE_ESCALATION = 'TASK_TYPE_ESCALATION'


class Resource(db.Model):
    __tablename__ = "rbac_resources"

    id = db.Column('id', db.String, primary_key=True)
    name = db.Column('name', db.String, nullable=False)
    description = db.Column('description', db.String)
    created_at = db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)

    def __init__(
            self,
            id: str,
            name: str,
            description: str
    ):
        self.id = id
        self.name = name
        self.description = description

    def as_dict(self) -> dict:
        """
        :return: The dict repr of a Resource object
        """
        return {
            "id":  self.id,
            "name": self.name,
            "description": self.description
        }
