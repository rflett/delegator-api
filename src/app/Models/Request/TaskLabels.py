from flask_restplus import fields

from app import api

task_label_dto = api.model("Task Label Dto", {
    "id": fields.Integer(),
    "label": fields.String(),
    "colour": fields.String()
})

new_task_label_dto = api.model("New Task Label Dto", {
    "label": fields.String(),
    "colour": fields.String()
})

