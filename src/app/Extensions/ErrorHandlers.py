from flask import jsonify, current_app


def handle_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    current_app.logger.info(error.to_dict())
    return response
