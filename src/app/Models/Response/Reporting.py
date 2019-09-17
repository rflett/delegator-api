from flask_restplus import fields

from app import api


task_trend_dto = api.model("Report Trend", {
    "title": fields.String,
    "today": fields.Integer,
    "yesterday": fields.Integer,
    "this_week": fields.Integer,
    "this_month": fields.Integer
})

task_time_dto = api.model("Report Time", {
    "task_type": fields.String,
    "time_to_start": fields.Integer,
    "time_to_finish": fields.Integer
})

slowest_dto = api.model("Report Slowest", {
    "task_id": fields.Integer,
    "finished_by": fields.String,
    "task_type": fields.String,
    "time_to_finish": fields.Integer
})

completed_dto = api.model("Report Completed", {
    "finished_by": fields.String,
    "task_type": fields.String,
    "finished_at": fields.DateTime
})

status_dto = api.model("Report Status", {
    "assignee": fields.String,
    "task_type": fields.String,
    "status": fields.String,
    "status_changed_at": fields.DateTime
})

priority_dto = api.model("Report Priority", {
    "assignee": fields.String,
    "task_type": fields.String,
    "priority": fields.String,
    "priority_changed_at": fields.DateTime
})

delays_dto = api.model("Report Delays", {
    "task_type": fields.String,
    "delayed_For": fields.Integer
})

get_all_reports_response = api.model("Get All Reports Request", {
    'trends': fields.Nested(task_trend_dto),
    'times': fields.Nested(task_time_dto),
    'slowest': fields.Nested(slowest_dto),
    'time_to_start': fields.Integer,
    'completed': fields.Nested(completed_dto),
    'priority': fields.Nested(priority_dto),
    'status': fields.Nested(status_dto),
    'delays': fields.Nested(delays_dto),
})
