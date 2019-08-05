class Error(Exception):
    """Base exception to inherit from"""
    pass


class AuthenticationError(Error):
    """Error for when there's issues related ot authentication"""
    pass


class AuthorizationError(Error):
    """Error for when there's issues related ot authorization"""
    pass


class ValidationError(Error):
    """Error for when there's issues related ot validation"""
    pass
