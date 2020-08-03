import structlog
from flask import jsonify


def handle_error(error):
    log = structlog.getLogger()
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    log.info(error.to_dict())
    return response
