class Error(Exception):
    """Base exception to inherit from"""

    pass


class AuthenticationError(Error):
    """Error for when there's issues related to authentication"""

    pass


class AuthorizationError(Error):
    """Error for when there's issues related to authorization"""

    pass


class ValidationError(Error):
    """Error for when there's issues related to validation"""

    pass


class ProductTierLimitError(Error):
    """Error for when a user tries to do something that is outside of their product tier"""

    pass


class WrapperCallFailedException(Error):
    """Error when a call to another API via a wrapper fails"""

    pass


class ResourceNotFoundError(Error):
    """Error when the requested resource is not found"""

    pass
