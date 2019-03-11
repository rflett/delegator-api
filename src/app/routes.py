from app import app, g_response
from functools import wraps
from flask import Response, request
from app.Controllers import AuthController, UserController, SignupController, TaskController, VersionController, \
    ActiveUserController
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


@app.route('/health', methods=['GET'])
def health():
    return g_response("yeet")


@app.route('/v', methods=['GET'])
def version_info():
    return VersionController.get_version_details()


@app.route('/login', methods=['POST'])
def login():
    return AuthController.login(request.get_json())


@app.route('/logout', methods=['POST'])
@requires_jwt
def logout():
    return AuthController.logout(request.headers)


@app.route('/reset_password', methods=['POST'])
def reset_password():
    return AuthController.reset_password(request.get_json())


@app.route('/signup', methods=['POST'])
def signup():
    return SignupController.signup(request)


@app.route('/users', methods=['POST'])
@requires_jwt
def user_create():
    return UserController.user_create(request)


@app.route('/users', methods=['GET'])
@requires_jwt
def get_users():
    return UserController.user_get_all(request)


@app.route('/users/active', methods=['GET'])
@requires_jwt
def active_users():
    return ActiveUserController.get_active_users()


@app.route('/user/<identifier>', methods=['GET'])
@requires_jwt
def get_user(identifier):
    return UserController.user_get(identifier, request)


@app.route('/user/<user_id>', methods=['PUT'])
@requires_jwt
def update_user(user_id):
    return UserController.user_update(user_id, request)


@app.route('/user/pages', methods=['GET'])
@requires_jwt
def user_pages():
    return UserController.user_pages(request)


@app.route('/roles', methods=['GET'])
@requires_jwt
def get_roles():
    return RoleController.get_roles(request)


@app.route('/tasks/priorities', methods=['GET'])
@requires_jwt
def get_task_priorities():
    return TaskController.get_task_priorities(request)


@app.route('/tasks/statuses', methods=['GET'])
@requires_jwt
def get_task_statuses():
    return TaskController.get_task_statuses(request)


@app.route('/tasks/types', methods=['GET'])
@requires_jwt
def get_task_types():
    return TaskController.get_task_types(request)


@app.route('/tasks/types', methods=['POST'])
@requires_jwt
def create_task_types():
    return TaskController.create_task_types(request)


@app.route('/tasks', methods=['POST'])
@requires_jwt
def create_task():
    return TaskController.task_create(request)


@app.route('/reporting/all', methods=['GET'])
@requires_jwt
def get_all_reports():
    return Reports.get_all(request)
