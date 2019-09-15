from app.Controllers.Authenticated import active_user_route, notification_token_route, org_route, report_route
from app.Controllers.Public import account_route, health_route

__all__ = [
    account_route,
    health_route,
    active_user_route,
    notification_token_route,
    org_route,
    report_route
]

# Import this to loop through and add all routes on initial server instantiation
all_routes = __all__
