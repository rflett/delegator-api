from os import getenv

from flask import url_for
from flask_restx import Api

from app.Controllers.Public.AccountController import api as account_v1
from app.Controllers.Public.ContactUsController import api as contact_v1
from app.Controllers.Public.HealthController import api as health_v1
from app.Controllers.Public.VersionController import api as version_v1
from app.Controllers.Public.ManagePasswordController import api as password_v1
from app.Controllers.Authenticated.ActiveUsers import api as active_users_v1
from app.Controllers.Authenticated.Roles import api as roles_v1
from app.Controllers.Authenticated.Organisation import api as organisation_v1
from app.Controllers.Authenticated.Task.AssignTaskController import api as assign_task_v1
from app.Controllers.Authenticated.Task.CancelTaskController import api as cancel_task_v1
from app.Controllers.Authenticated.Task.DelayTaskController import api as delay_task_v1
from app.Controllers.Authenticated.Task.DropTaskController import api as drop_task_v1
from app.Controllers.Authenticated.Task.TaskActivityController import api as task_activity_v1
from app.Controllers.Authenticated.Task.TaskController import api as task_v1
from app.Controllers.Authenticated.Task.TaskLabelsController import api as task_labels_v1
from app.Controllers.Authenticated.Task.TaskPrioritiesController import api as task_priorities_v1
from app.Controllers.Authenticated.Task.TaskTemplatesController import api as task_templates_v1
from app.Controllers.Authenticated.Task.TaskEscalationPolicyController import api as template_escalations_v1
from app.Controllers.Authenticated.Task.TasksController import api as tasks_v1
from app.Controllers.Authenticated.Task.TransitionTaskController import api as transition_task_v1
from app.Controllers.Authenticated.User.UserActivityController import api as user_activity_v1
from app.Controllers.Authenticated.User.UserController import api as user_v1
from app.Controllers.Authenticated.User.UserPagesController import api as user_pages_v1
from app.Controllers.Authenticated.User.UserAvatarController import api as user_avatar_v1
from app.Controllers.Authenticated.User.UsersController import api as users_v1
from app.Controllers.Authenticated.User.UserSettingsController import api as user_settings_v1
from app.Controllers.Authenticated.User.UserWelcomeController import api as user_welcome_v1
from app.Controllers.Authenticated.User.DisableUserController import api as disable_user_v1


# swagger monkey patch
if getenv("APP_ENV", "Local") in ["Staging", "Production"]:

    @property
    def specs_url(self):
        """Monkey patch for HTTPS"""
        return url_for(self.endpoint("specs"), _external=True, _scheme="https")

    Api.specs_url = specs_url

api = Api(title="Delegator API", version="1.0", description="The API to get Delegating")

api.add_namespace(account_v1)
api.add_namespace(active_users_v1)
api.add_namespace(contact_v1)
api.add_namespace(organisation_v1)
api.add_namespace(password_v1)
api.add_namespace(roles_v1)
api.add_namespace(assign_task_v1)
api.add_namespace(cancel_task_v1)
api.add_namespace(delay_task_v1)
api.add_namespace(drop_task_v1)
api.add_namespace(task_activity_v1)
api.add_namespace(task_v1)
api.add_namespace(task_labels_v1)
api.add_namespace(task_priorities_v1)
api.add_namespace(task_templates_v1)
api.add_namespace(template_escalations_v1)
api.add_namespace(tasks_v1)
api.add_namespace(transition_task_v1)
api.add_namespace(user_activity_v1)
api.add_namespace(user_v1)
api.add_namespace(user_pages_v1)
api.add_namespace(user_avatar_v1)
api.add_namespace(users_v1)
api.add_namespace(user_settings_v1)
api.add_namespace(user_welcome_v1)
api.add_namespace(disable_user_v1)
api.add_namespace(health_v1)
api.add_namespace(version_v1)
