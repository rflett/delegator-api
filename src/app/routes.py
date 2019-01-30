from app import app, logger
from functools import wraps
from flask import Response, request
from app.Controllers import AuthController, ExampleController, UserController, OrganisationController, SignupController


def requires_jwt(f):
    """
    Decorator that checks that the request contains a JWT token in the Authorization header.
    This won't validate the user, just make sure there is a token.
    :return: Either a response (usually 403) or the decorated function.
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
    return Response(status=200)


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


@app.route('/signup', methods=['POST'])
def signup():
    """
    Handles signup

    :return: Response
    """
    return SignupController.signup(request)


@app.route('/user/create', methods=['POST'])
@requires_jwt
def user_create():
    """
    Handles creating a user.

    :return: Response
    """
    return UserController.create_user(request)


@app.route('/org/create', methods=['POST'])
@requires_jwt
def org_create():
    """
    Handles creating an organisation.
    
    :return: Response
    """
    return OrganisationController.org_create(request)


@app.route('/example', methods=['GET'])
@requires_jwt
def example():
    """
    An example route which can be a basis for other routes moving forward.
    :return: Response
    """
    return ExampleController.example(request)
