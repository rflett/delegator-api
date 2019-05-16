class Events(str):
    """
    These events are added as both a payload attribute to the SNS message, but also as a message attribute.

    MessageAttributes={
        'event': {
            'DataType': 'String',
            'StringValue': self.event
        },
        'event_class': {
            'DataType': 'String',
            'StringValue': self.event.split('_')[0]
        }
    }

    The event class is the characters before the first underscore.

    """
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

    task_escalated = 'task_escalated'

    task_delay_finished = 'task_delay_finished'

    tasktype_created = 'tasktype_created'
    tasktype_enabled = 'tasktype_enabled'
    tasktype_disabled = 'tasktype_disabled'
    tasktype_escalation_created = 'tasktype_escalation_created'
