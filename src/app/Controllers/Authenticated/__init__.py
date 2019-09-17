from app.Controllers.Authenticated.ActiveUsers import active_user_route
from app.Controllers.Authenticated.Activity import activity_route
from app.Controllers.Authenticated.NotificationToken import notification_token_route
from app.Controllers.Authenticated.Organisation import org_route
from app.Controllers.Authenticated.Reporting import report_route
from app.Controllers.Authenticated.Roles import roles_route
from app.Controllers.Authenticated.Task.AssignTask import assign_task_route
from app.Controllers.Authenticated.Task.CancelTask import cancel_task_route
from app.Controllers.Authenticated.Task.DelayTask import delay_task_route
from app.Controllers.Authenticated.Task.DropTask import drop_task_route
from app.Controllers.Authenticated.Task.Tasks import tasks_route
from app.Controllers.Authenticated.Task.TaskPriorities import task_priorities_route
from app.Controllers.Authenticated.Task.TransitionTask import transition_task_route
from app.Controllers.Authenticated.Task.TaskStatuses import task_statuses_route
from app.Controllers.Authenticated.Task.TaskTypes import task_types_route

all_authenticated = [
    assign_task_route,
    cancel_task_route,
    delay_task_route,
    drop_task_route,
    active_user_route,
    activity_route,
    notification_token_route,
    org_route,
    report_route,
    task_statuses_route,
    task_priorities_route,
    task_types_route,
    tasks_route,
    transition_task_route,
    roles_route
]
