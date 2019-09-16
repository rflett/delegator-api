from flask_restplus import fields

from app import api

# TODO use this for nullable date times
# class NullableString(fields.String):
#     __schema_type__ = ['string', 'null']
#     __schema_example__ = 'nullable string'

update_task_dto = api.model("Update Task Model", {
    'id': fields.Integer(),
    'type_id': fields.Integer(),
    'description': fields.String(),
    'status': fields.String(),
    'time_estimate': fields.Integer(),
    'due_time': fields.DateTime(),
    'assignee': fields.Integer(),
    'priority': fields.Integer(),
})

create_task_dto = api.model("Create Task Model", {
    'type_id': fields.Integer(),
    'description': fields.String(),
    'status': fields.String(),
    'time_estimate': fields.Integer(),
    'due_time': fields.DateTime(),
    'assignee': fields.Integer(),
    'priority': fields.Integer(),
})
