from app.Controllers.Public.AccountController import account_route
from app.Controllers.Public.HealthController import health_route
from app.Controllers.Public.VersionController import version_route

all_public = [
    account_route,
    health_route,
    version_route
]
