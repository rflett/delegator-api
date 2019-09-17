from app.Controllers.Authenticated import all_authenticated
from app.Controllers.Public import all_public

# Import this to loop through and add all routes on initial server instantiation
all_routes = all_authenticated + all_public
