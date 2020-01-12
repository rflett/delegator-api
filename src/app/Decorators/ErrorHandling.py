import json
import traceback
from functools import wraps

import requests
from flask import Response
from werkzeug.exceptions import BadRequest, NotFound, MethodNotAllowed, HTTPException

import app.Exceptions as Exceptions
from app import logger


def handle_exceptions(f):
    """ Handles custom exceptions and unexpected errors """

    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except requests.Timeout as e:
            logger.error(str(e))
            return Response(json.dumps({"msg": str(e)}), status=202, headers={"Content-Type": "application/json"})

        except (Exceptions.ValidationError, BadRequest) as e:
            logger.info(str(e))
            return Response(json.dumps({"msg": str(e)}), status=400, headers={"Content-Type": "application/json"})

        except Exceptions.AuthenticationError as e:
            logger.info(str(e))
            return Response(json.dumps({"msg": str(e)}), status=401, headers={"Content-Type": "application/json"})

        except Exceptions.ProductTierLimitError as e:
            logger.info(str(e))
            return Response(json.dumps({"msg": str(e)}), status=402, headers={"Content-Type": "application/json"})

        except Exceptions.AuthorizationError as e:
            logger.info(str(e))
            return Response(json.dumps({"msg": str(e)}), status=403, headers={"Content-Type": "application/json"})

        except (Exceptions.ResourceNotFoundError, NotFound) as e:
            logger.info(str(e))
            return Response(json.dumps({"msg": str(e)}), status=404, headers={"Content-Type": "application/json"})

        except MethodNotAllowed as e:
            logger.info(str(e))
            return Response(json.dumps({"msg": str(e)}), status=405, headers={"Content-Type": "application/json"})

        except (Exceptions.WrapperCallFailedException, HTTPException) as e:
            logger.error(str(e))
            return Response(json.dumps({"msg": str(e)}), status=422, headers={"Content-Type": "application/json"})

        except Exception as e:
            logger.error(traceback.format_exc())
            return Response(json.dumps({"msg": str(e)}), status=500, headers={"Content-Type": "application/json"})

    return decorated
