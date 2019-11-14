from app.Controllers.Authenticated.Task.AssignTaskController import assign_task_route
from app.Controllers.Authenticated.Task.CancelTaskController import cancel_task_route
from app.Controllers.Authenticated.Task.DelayTaskController import delay_task_route
from app.Controllers.Authenticated.Task.DropTaskController import drop_task_route
from app.Controllers.Authenticated.Task.TasksController import tasks_route
from app.Controllers.Authenticated.Task.TaskLabelsController import task_labels_route
from app.Controllers.Authenticated.Task.TaskPrioritiesController import task_priorities_route
from app.Controllers.Authenticated.Task.TransitionTaskController import transition_task_route
from app.Controllers.Authenticated.Task.TaskStatusesController import task_statuses_route
from app.Controllers.Authenticated.Task.TaskTypesController import task_types_route
from app.Controllers.Authenticated.Task.TaskActivityController import task_activity_route
from app.Controllers.Authenticated.Task.TaskController import task_route

all_task_routes = [
    assign_task_route,
    cancel_task_route,
    delay_task_route,
    drop_task_route,
    task_labels_route,
    task_statuses_route,
    task_priorities_route,
    task_types_route,
    tasks_route,
    transition_task_route,
    task_activity_route,
    task_route
]
