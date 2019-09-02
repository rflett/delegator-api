import traceback
from functools import wraps

import requests

import app.Exceptions as Exceptions
from app import logger, g_response


def handle_exceptions(f):
    """ Handles custom exceptions and unexpected errors """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.Timeout as e:
            logger.error(str(e))
            return g_response(msg=str(e), status=202)
        except Exceptions.ValidationError as e:
            logger.info(str(e))
            return g_response(msg=str(e), status=400)
        except Exceptions.AuthenticationError as e:
            logger.info(str(e))
            return g_response(msg=str(e), status=401)
        except Exceptions.ProductTierLimitError as e:
            logger.info(str(e))
            return g_response(msg=str(e), status=402)
        except Exceptions.AuthorizationError as e:
            logger.info(str(e))
            return g_response(msg=str(e), status=403)
        except Exceptions.WrapperCallFailedException as e:
            logger.error(str(e))
            return g_response(msg=str(e), status=500)
        except Exception as e:
            logger.error(traceback.format_exc())
            return g_response(msg=str(e), status=500)
    return decorated
