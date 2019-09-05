from app.Middleware import handle_exceptions, requires_jwt

from flask import request

from app import app
from app.Controllers import TaskController, TaskTypeController


@app.route('/task/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task(task_id):
    return TaskController.get_task(task_id, request)


@app.route('/task/assign', methods=['POST'])
@requires_jwt
@handle_exceptions
def assign_task():
    return TaskController.assign_task(request)


@app.route('/task/drop/<int:task_id>', methods=['POST'])
@requires_jwt
@handle_exceptions
def drop_task(task_id):
    return TaskController.drop_task(task_id=task_id, req=request)


@app.route('/task/cancel/<int:task_id>', methods=['POST'])
@requires_jwt
@handle_exceptions
def cancel_task(task_id):
    return TaskController.cancel_task(task_id, request)


@app.route('/task/transition', methods=['POST'])
@requires_jwt
@handle_exceptions
def transition_task():
    return TaskController.transition_task(request)


@app.route('/task/transition/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_available_transitions(task_id):
    return TaskController.get_available_transitions(task_id, request)


@app.route('/task/delay', methods=['POST'])
@requires_jwt
@handle_exceptions
def delay_task():
    return TaskController.delay_task(request)


@app.route('/task/delay/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_delayed_task(task_id):
    return TaskController.get_delayed_task(task_id, request)


@app.route('/task/activity/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_activity(task_id):
    return TaskController.get_task_activity(task_id, request)


@app.route('/tasks/priorities', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_priorities():
    return TaskController.get_task_priorities(request)


@app.route('/tasks/statuses', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_statuses():
    return TaskController.get_task_statuses(request)


@app.route('/tasks/types', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_types():
    return TaskTypeController.get_task_types(request)


@app.route('/tasks/types', methods=['PUT'])
@requires_jwt
@handle_exceptions
def create_task_type():
    return TaskTypeController.create_task_type(request)


@app.route('/tasks/types', methods=['POST'])
@requires_jwt
@handle_exceptions
def update_task_type():
    return TaskTypeController.update_task_type(request)


@app.route('/tasks/types/<int:task_type_id>', methods=['DELETE'])
@requires_jwt
@handle_exceptions
def disable_task_type(task_type_id):
    return TaskTypeController.disable_task_type(task_type_id, request)


@app.route('/tasks', methods=['POST'])
@requires_jwt
@handle_exceptions
def create_task():
    return TaskController.create_task(request)


@app.route('/tasks', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_tasks():
    return TaskController.get_tasks(request)


@app.route('/tasks', methods=['PUT'])
@requires_jwt
@handle_exceptions
def update_task():
    return TaskController.update_task(request)
