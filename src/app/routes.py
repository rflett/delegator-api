import traceback
from functools import wraps

from flask import Response, request

from app import app, g_response, logger
from app.Exceptions import AuthenticationError, AuthorizationError
from app.Controllers import AuthorizationController, UserController, SignupController, TaskController, \
    VersionController, ActiveUserController, OrganisationController, TaskTypeController, AuthenticationController, \
    RoleController, ReportController


def requires_jwt(f):
    """
    Decorator that checks that the request contains a JWT token in the Authorization header.
    This won't validate the user, just make sure there is a token.
    :return: Either a response (usually 401) or the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        check = AuthenticationController.check_authorization_header(auth)
        if isinstance(check, Response):
            return check
        else:
            return f(*args, **kwargs)
    return decorated


def safe_exceptions(f):
    """ Handles custom exceptions and unexpected errors """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AuthenticationError as e:
            return g_response(msg=str(e), status=401)
        except Exception as e:
            logger.error(traceback.format_exc())
            return g_response(msg=str(e), status=500)
    return decorated


@app.route('/health', methods=['GET'])
@safe_exceptions
def health():
    return g_response("yeet")


@app.route('/v', methods=['GET'])
@safe_exceptions
def version_info():
    return VersionController.get_version_details()


@app.route('/login', methods=['POST'])
@safe_exceptions
def login():
    return AuthenticationController.login(request)


@app.route('/logout', methods=['POST'])
@requires_jwt
@safe_exceptions
def logout():
    return AuthenticationController.logout(request.headers)


@app.route('/reset_password', methods=['POST'])
@safe_exceptions
def reset_password():
    return AuthorizationController.reset_password(request)


@app.route('/signup', methods=['POST'])
@safe_exceptions
def signup():
    return SignupController.signup(request)


@app.route('/users', methods=['POST'])
@requires_jwt
@safe_exceptions
def create_user():
    return UserController.create_user(request)


@app.route('/users', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_users():
    return UserController.get_all_users(request)


@app.route('/users', methods=['PUT'])
@requires_jwt
@safe_exceptions
def update_user():
    return UserController.update_user(request)


@app.route('/users/active', methods=['GET'])
@requires_jwt
@safe_exceptions
def active_users():
    return ActiveUserController.get_active_users(request)


@app.route('/user/<user_id>', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_user(user_id):
    return UserController.get_user(user_id, request)


@app.route('/user/<int:user_id>', methods=['DELETE'])
@requires_jwt
@safe_exceptions
def delete_user(user_id):
    return UserController.delete_user(user_id, request)


@app.route('/user/pages', methods=['GET'])
@requires_jwt
@safe_exceptions
def user_pages():
    return UserController.user_pages(request)


@app.route('/user/settings', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_user_settings():
    return UserController.get_user_settings(request)


@app.route('/user/settings', methods=['PUT'])
@requires_jwt
@safe_exceptions
def update_user_settings():
    return UserController.update_user_settings(request)


@app.route('/user/activity/<user_id>', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_user_activity(user_id):
    return UserController.get_user_activity(user_id, request)


@app.route('/roles', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_roles():
    return RoleController.get_roles(request)


@app.route('/tasks/priorities', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_task_priorities():
    return TaskController.get_task_priorities(request)


@app.route('/tasks/statuses', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_task_statuses():
    return TaskController.get_task_statuses(request)


@app.route('/tasks/types', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_task_types():
    return TaskTypeController.get_task_types(request)


@app.route('/tasks/types', methods=['POST'])
@requires_jwt
@safe_exceptions
def create_task_type():
    return TaskTypeController.create_task_type(request)


@app.route('/tasks/types/<int:task_type_id>', methods=['DELETE'])
@requires_jwt
@safe_exceptions
def disable_task_type(task_type_id):
    return TaskTypeController.disable_task_type(task_type_id, request)


@app.route('/tasks/types/escalation', methods=['POST'])
@requires_jwt
@safe_exceptions
def update_task_type_escalation():
    return TaskTypeController.upsert_task_escalations(request)


@app.route('/tasks', methods=['POST'])
@requires_jwt
@safe_exceptions
def create_task():
    return TaskController.create_task(request)


@app.route('/tasks', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_tasks():
    return TaskController.get_tasks(request)


@app.route('/tasks', methods=['PUT'])
@requires_jwt
@safe_exceptions
def update_task():
    return TaskController.update_task(request)


@app.route('/task/<int:task_id>', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_task(task_id):
    return TaskController.get_task(task_id, request)


@app.route('/task/assign', methods=['POST'])
@requires_jwt
@safe_exceptions
def assign_task():
    return TaskController.assign_task(request)


@app.route('/task/drop/<int:task_id>', methods=['POST'])
@requires_jwt
@safe_exceptions
def drop_task(task_id):
    return TaskController.drop_task(task_id, request)


@app.route('/task/transition', methods=['POST'])
@requires_jwt
@safe_exceptions
def transition_task():
    return TaskController.transition_task(request)


@app.route('/task/delay', methods=['POST'])
@requires_jwt
@safe_exceptions
def delay_task():
    return TaskController.delay_task(request)


@app.route('/task/activity/<int:task_id>', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_task_activity(task_id):
    return TaskController.get_task_activity(task_id, request)


@app.route('/org/settings', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_org_settings():
    return OrganisationController.get_org_settings(request)


@app.route('/org/settings', methods=['PUT'])
@requires_jwt
@safe_exceptions
def update_org_settings():
    return OrganisationController.update_org_settings(request)


@app.route('/reporting/all', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_all_reports():
    return ReportController.get_all(request)
