class Events(str):
    user_login = 'user_login'
    user_logout = 'user_logout'
    user_created = 'user_created'
    user_updated = 'user_updated'
    user_deleted = 'user_deleted'

    task_transitioned_inprogress = 'task_transitioned_inprogress'
    task_transitioned_ready = 'task_transitioned_ready'
    task_transitioned_cancelled = 'task_transitioned_cancelled'
    task_transitioned_delayed = 'task_transitioned_delayed'
    task_transitioned_completed = 'task_transitioned_completed'
    task_created = 'task_created'
    task_updated = 'task_updated'
    task_assigned = 'task_assigned'

    task_type_created = 'task_type_created'
    task_type_enabled = 'task_type_enabled'
    task_type_disabled = 'task_type_disabled'
    task_type_escalation_created = 'task_type_escalation_created'
