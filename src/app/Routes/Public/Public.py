from app.Middleware import handle_exceptions

from flask import request

from app import app, g_response
from app.Controllers import AuthenticationController, VersionController, AuthorizationController, SignupController


@app.route('/health', methods=['GET'])
@handle_exceptions
def health():
    return g_response("yeet")


@app.route('/login', methods=['POST'])
@handle_exceptions
def login():
    return AuthenticationController.login(request)


@app.route('/v', methods=['GET'])
@handle_exceptions
def version_info():
    return VersionController.get_version_details()


@app.route('/reset_password', methods=['POST'])
@handle_exceptions
def reset_password():
    return AuthorizationController.reset_password(request)


@app.route('/signup', methods=['POST'])
@handle_exceptions
def signup():
    return SignupController.signup(request)
