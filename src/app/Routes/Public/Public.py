from app.Decorators import handle_exceptions

from app import app
from app.Controllers import AuthorizationController, SignupController
from app.Controllers.Public import VersionController


@app.route('/v', methods=['GET'])
@handle_exceptions
def version_info():
    return VersionController.get_version_details()


@app.route('/reset_password', methods=['POST'])
@handle_exceptions
def reset_password():
    return AuthorizationController.reset_password()


@app.route('/signup', methods=['POST'])
@handle_exceptions
def signup():
    return SignupController.signup()
