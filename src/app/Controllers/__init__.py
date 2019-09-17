from app.Controllers.Authenticated import active_user_route, notification_token_route, org_route, report_route, \
    tasks_route, activity_route, roles_route, task_priorities_route, task_statuses_route, transition_task_route, \
    drop_task_route, delay_task_route, cancel_task_route, assign_task_route, task_types_route
from app.Controllers.Public import account_route, health_route
from app.Controllers.Public.VersionController import version_route

__all__ = [
    active_user_route,
    assign_task_route,
    account_route,
    activity_route,
    cancel_task_route,
    delay_task_route,
    drop_task_route,
    health_route,
    notification_token_route,
    org_route,
    report_route,
    roles_route,
    task_priorities_route,
    task_statuses_route,
    task_types_route,
    tasks_route,
    transition_task_route,
    version_route
]

# Import this to loop through and add all routes on initial server instantiation
all_routes = __all__
