from app.Middleware import handle_exceptions, requires_jwt

from app import app
from app.Controllers import TaskController, TaskTypeController


@app.route('/task/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task(task_id, **kwargs):
    return TaskController.get_task(task_id, **kwargs)


@app.route('/task/assign', methods=['POST'])
@requires_jwt
@handle_exceptions
def assign_task(**kwargs):
    return TaskController.assign_task(**kwargs)


@app.route('/task/drop/<int:task_id>', methods=['POST'])
@requires_jwt
@handle_exceptions
def drop_task(task_id, **kwargs):
    return TaskController.drop_task(task_id, **kwargs)


@app.route('/task/cancel/<int:task_id>', methods=['POST'])
@requires_jwt
@handle_exceptions
def cancel_task(task_id, **kwargs):
    return TaskController.cancel_task(task_id, **kwargs)


@app.route('/task/transition', methods=['POST'])
@requires_jwt
@handle_exceptions
def transition_task(**kwargs):
    return TaskController.transition_task(**kwargs)


@app.route('/task/transition/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_available_transitions(task_id, **kwargs):
    return TaskController.get_available_transitions(task_id, **kwargs)


@app.route('/task/delay', methods=['POST'])
@requires_jwt
@handle_exceptions
def delay_task(**kwargs):
    return TaskController.delay_task(**kwargs)


@app.route('/task/delay/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_delayed_task(task_id, **kwargs):
    return TaskController.get_delayed_task(task_id, **kwargs)


@app.route('/task/activity/<int:task_id>', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_activity(task_id, **kwargs):
    return TaskController.get_task_activity(task_id, **kwargs)


@app.route('/tasks/priorities', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_priorities(**kwargs):
    return TaskController.get_task_priorities(**kwargs)


@app.route('/tasks/statuses', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_statuses(**kwargs):
    return TaskController.get_task_statuses(**kwargs)


@app.route('/tasks/types', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_task_types(**kwargs):
    return TaskTypeController.get_task_types(**kwargs)


@app.route('/tasks/types', methods=['PUT'])
@requires_jwt
@handle_exceptions
def create_task_type(**kwargs):
    return TaskTypeController.create_task_type(**kwargs)


@app.route('/tasks/types', methods=['POST'])
@requires_jwt
@handle_exceptions
def update_task_type(**kwargs):
    return TaskTypeController.update_task_type(**kwargs)


@app.route('/tasks/types/<int:task_type_id>', methods=['DELETE'])
@requires_jwt
@handle_exceptions
def disable_task_type(task_type_id, **kwargs):
    return TaskTypeController.disable_task_type(task_type_id, **kwargs)


@app.route('/tasks', methods=['POST'])
@requires_jwt
@handle_exceptions
def create_task(**kwargs):
    return TaskController.create_task(**kwargs)


@app.route('/tasks', methods=['GET'])
@requires_jwt
@handle_exceptions
def get_tasks(**kwargs):
    return TaskController.get_tasks(**kwargs)


@app.route('/tasks', methods=['PUT'])
@requires_jwt
@handle_exceptions
def update_task(**kwargs):
    return TaskController.update_task(**kwargs)
