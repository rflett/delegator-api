from flask_restplus import fields

from app import api

activity_dto = api.model(
    "Activity", {"activity": fields.String(), "activity_timestamp": fields.String(), "event_friendly": fields.String(),}
)

activity_response_dto = api.model("Activity Model", {"activity": fields.List(fields.Nested(activity_dto))})
