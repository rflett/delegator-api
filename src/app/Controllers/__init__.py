from app.Controllers.ActiveUserController import active_user_route

__all__ = [
    active_user_route
]

# Import this to loop through and add all routes on initial server instantiation
all_routes = __all__
