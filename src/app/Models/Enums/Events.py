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
        'push': {
            'DataType': 'String',
            'StringValue': message.get('push', 'false')
        }
    }

    The event class is the characters before the first underscore.

    """

    user_assigned_task = "user_assigned_task"
    user_assigned_to_task = "user_assigned_to_task"
    user_unassigned_task = "user_unassigned_task"
    user_unassigned_from_task = "user_unassigned_from_task"
    user_login = "user_login"
    user_logout = "user_logout"
    user_created = "user_created"
    user_created_user = "user_created_user"
    user_created_task = "user_created_task"
    user_scheduled_task = "user_scheduled_task"
    user_created_tasktemplate = "user_created_tasktemplate"
    user_created_tasktemplate_escalation = "user_created_tasktemplate_escalation"
    user_updated_tasktemplate_escalation = "user_updated_tasktemplate_escalation"
    user_deleted_tasktemplate_escalation = "user_deleted_tasktemplate_escalation"
    user_updated = "user_updated"
    user_updated_user = "user_updated_user"
    user_deleted = "user_deleted"
    user_deleted_user = "user_deleted_user"
    user_enabled_user = "user_enabled_user"
    user_disabled_user = "user_disabled_user"
    user_disabled_tasktemplate = "user_disabled_tasktemplate"
    user_transitioned_task = "user_transitioned_task"

    task_transitioned_inprogress = "task_transitioned_inprogress"
    task_transitioned_ready = "task_transitioned_ready"
    task_transitioned_cancelled = "task_transitioned_cancelled"
    task_transitioned_delayed = "task_transitioned_delayed"
    task_transitioned_completed = "task_transitioned_completed"
    task_created = "task_created"
    task_scheduled = "task_scheduled"
    task_updated = "task_updated"
    task_assigned = "task_assigned"
    task_unassigned = "task_unassigned"
    task_repositioned = "task_repositioned"

    task_escalated = "task_escalated"

    task_delay_finished = "task_delay_finished"
