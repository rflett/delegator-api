class Error(Exception):
    pass


class AuthenticationError(Error):
    pass


class AuthorizationError(Error):
    pass
