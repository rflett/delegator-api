from flask_restplus import fields

from app import api

task_label_dto = api.model(
    "Task Label Dto", {"id": fields.Integer(), "label": fields.String(), "colour": fields.String()}
)

task_labels_response = api.model("Task Labels Response", {"labels": fields.List(fields.Nested(task_label_dto))})
