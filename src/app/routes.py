from app import app, g_response
from functools import wraps
from flask import Response, request
from app.Controllers import AuthController, UserController, OrganisationController, SignupController


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
    """
    Health endpoint, required for load balancers etc.
    :return: OK Response"
    """
    return g_response("yeet")


@app.route('/login', methods=['POST'])
def login():
    """
    Handles user login.
    :return: Response
    """
    return AuthController.login(request.get_json())


@app.route('/logout', methods=['POST'])
@requires_jwt
def logout():
    """
    Handles user logout.
    :return: Response
    """
    return AuthController.logout(request.headers)


@app.route('/reset_password', methods=['POST'])
def reset_password():
    """
    Handles resetting a forgotten password
    :return: Response
    """
    return AuthController.reset_password(request.get_json())


@app.route('/signup', methods=['POST'])
def signup():
    """
    Handles signup
    :return: Response
    """
    return SignupController.signup(request)


@app.route('/user', methods=['POST'])
@requires_jwt
def user_create():
    """
    Handles creating a user.
    :return: Response
    """
    return UserController.user_create(request)


@app.route('/user', methods=['PUT'])
@requires_jwt
def update_user():
    """
    Handles updating a user
    :return: Response
    """
    return UserController.user_update(request)


@app.route('/user/<identifier>', methods=['GET'])
@requires_jwt
def get_user(identifier):
    """
    Handles getting a single user
    :return:
    """
    return UserController.user_get(identifier, request)


@app.route('/org', methods=['POST'])
@requires_jwt
def org_create():
    """
    Handles creating an organisation.
    :return: Response
    """
    return OrganisationController.org_create(request)
