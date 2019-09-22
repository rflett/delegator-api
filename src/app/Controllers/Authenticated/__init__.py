from app.Controllers.Authenticated.ActiveUsers import active_user_route
from app.Controllers.Authenticated.NotificationToken import notification_token_route
from app.Controllers.Authenticated.Organisation import org_route
from app.Controllers.Authenticated.Reporting import report_route
from app.Controllers.Authenticated.Roles import roles_route
from app.Controllers.Authenticated.Task import all_task_routes
from app.Controllers.Authenticated.User import all_user_routes

all_authenticated = [
    active_user_route,
    notification_token_route,
    org_route,
    report_route,
    roles_route
]
