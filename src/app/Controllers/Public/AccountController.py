from flask import Response, request
from flask_restplus import Namespace

from app import session_scope
from app.Controllers.Base import RequestValidationController

account_route = Namespace("Account", "Contains routes for logging in and registering", "/account")


@account_route.route("/")
class AccountController(RequestValidationController):

    @account_route.route("/login")
    def post(self) -> Response:
        """Log a user in."""
        # get params from http request
        request_body = request.get_json()
        email = request_body.get('email')
        password = request_body.get('password')

        # validate email
        self.validate_email(email)

        # validate password
        self.validate_password(password)

        with session_scope() as session:
            user = session.query(User).filter_by(email=email).first()

            if user is None:
                self._failed_login_attempt(email)
            else:
                user.clear_failed_logins()

            # don't let them log in if they are disabled
            if user.disabled is not None:
                logger.info(f"Disabled user {user.id} tried to log in.")
                raise AuthenticationError("Cannot log in since this account has been disabled. Please consult your "
                                          "Administrator for assistance.")

            # don't let them log in if they are deleted (unlikely to happen)
            if user.deleted is not None:
                logger.warning(f"Deleted user {user.id} tried to log in.")
                raise AuthenticationError(f"Email or password incorrect")

            # check login attempts
            if user.failed_login_attempts > 0:
                logger.info(f"User {user.id} has failed to log in "
                            f"{user.failed_login_attempts} / {app.config['FAILED_LOGIN_ATTEMPTS_MAX']} times.")
                if user.failed_login_attempts >= app.config['FAILED_LOGIN_ATTEMPTS_MAX']:
                    # check timeout
                    diff = (datetime.datetime.utcnow() - user.failed_login_time).seconds
                    if diff < app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']:
                        logger.info(f"user last failed {diff}s ago. "
                                    f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s")
                        raise AuthenticationError("Too many incorrect password attempts.")
                    else:
                        with session_scope():
                            # reset timeout
                            logger.info(f"User last failed {diff}s ago. "
                                        f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s.")
                            user.failed_login_attempts = 0
                            user.failed_login_time = None

            # check password
            if user.password_correct(password):
                # reset failed attempts
                user.failed_login_attempts = 0
                user.failed_login_time = None
                user.is_active()
                Activity(
                    org_id=user.org_id,
                    event=Events.user_login,
                    event_id=user.id,
                    event_friendly="Logged in."
                ).publish()

                # return the user dict and their JWT token
                return self.ok({
                    **user.fat_dict(),
                    **{"jwt": self._generate_jwt_token(user)}
                })
            else:
                logger.info(f"Incorrect password attempt for user {user.id}.")
                user.failed_login_attempts += 1
                user.failed_login_time = datetime.datetime.utcnow()
                raise AuthenticationError("Password incorrect.")
