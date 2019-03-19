import traceback
from app import app, g_response, logger
from functools import wraps
from flask import Response, request
from app.Controllers import AuthController, UserController, SignupController, TaskController, VersionController, \
    ActiveUserController, OrganisationController
from app.Controllers.RBAC import RoleController
from app.Controllers.Reporting import Reports


def requires_jwt(f):
    """
    Decorator that checks that the request contains a JWT token in the Authorization header.
    This won't validate the user, just make sure there is a token.
    :return: Either a response (usually 401) or the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        check = AuthController.check_authorization_header(auth)
        if isinstance(check, Response):
            return check
        else:
            return f(*args, **kwargs)
    return decorated


def safe_exceptions(f):
    """ Returns 500 if an exception is raised """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
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
    return AuthController.login(request.get_json())


@app.route('/logout', methods=['POST'])
@requires_jwt
@safe_exceptions
def logout():
    return AuthController.logout(request.headers)


@app.route('/reset_password', methods=['POST'])
@safe_exceptions
def reset_password():
    return AuthController.reset_password(request.get_json())


@app.route('/signup', methods=['POST'])
@safe_exceptions
def signup():
    return SignupController.signup(request)


@app.route('/users', methods=['POST'])
@requires_jwt
@safe_exceptions
def user_create():
    return UserController.user_create(request)


@app.route('/users', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_users():
    return UserController.user_get_all(request)


@app.route('/users/active', methods=['GET'])
@requires_jwt
@safe_exceptions
def active_users():
    return ActiveUserController.get_active_users()


@app.route('/user/<identifier>', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_user(identifier):
    return UserController.user_get(identifier, request)


@app.route('/user/<user_id>', methods=['PUT'])
@requires_jwt
@safe_exceptions
def update_user(user_id):
    return UserController.user_update(user_id, request)


@app.route('/user/<user_id>', methods=['DELETE'])
@requires_jwt
@safe_exceptions
def delete_user(user_id):
    return UserController.user_delete(user_id, request)


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
    return TaskController.get_task_types(request)


@app.route('/tasks/types', methods=['POST'])
@requires_jwt
@safe_exceptions
def create_task_types():
    return TaskController.create_task_types(request)


@app.route('/tasks/types/<task_type_id>', methods=['DELETE'])
@requires_jwt
@safe_exceptions
def disable_task_type(task_type_id):
    return TaskController.disable_task_type(task_type_id, request)


@app.route('/tasks', methods=['POST'])
@requires_jwt
@safe_exceptions
def create_task():
    return TaskController.task_create(request)


@app.route('/tasks', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_tasks():
    return TaskController.task_get_all(request)


@app.route('/task/<task_id>', methods=['PUT'])
@requires_jwt
@safe_exceptions
def update_task(task_id):
    return TaskController.task_update(task_id, request)


@app.route('/task/<task_id>', methods=['GET'])
@requires_jwt
@safe_exceptions
def get_task(task_id):
    return TaskController.task_get(task_id, request)


@app.route('/task/assign', methods=['POST'])
@requires_jwt
@safe_exceptions
def assign_task():
    return TaskController.assign_task(request)


@app.route('/task/drop/<task_id>', methods=['POST'])
@requires_jwt
@safe_exceptions
def drop_task(task_id):
    return TaskController.drop_task(task_id, request)


@app.route('/task/transition', methods=['POST'])
@requires_jwt
@safe_exceptions
def transition_task():
    return TaskController.transition_task(request)


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
    return Reports.get_all(request)
