class Error(Exception):
    pass


class AuthenticationError(Error):
    pass


class AuthorizationError(Error):
    pass


class ValidationError(Error):
    pass
