from app.Controllers.Authenticated.ActiveUsers import active_user_route
from app.Controllers.Authenticated.Activity import activity_route
from app.Controllers.Authenticated.NotificationToken import notification_token_route
from app.Controllers.Authenticated.Organisation import org_route
from app.Controllers.Authenticated.Reporting import report_route
from app.Controllers.Authenticated.RoleController import roles_route
from app.Controllers.Authenticated.Task import task_route
from app.Controllers.Authenticated.Tasks import tasks_route

__all__ = [
    active_user_route,
    activity_route,
    notification_token_route,
    org_route,
    report_route,
    task_route,
    tasks_route,
    roles_route
]
