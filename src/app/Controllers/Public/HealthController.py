from flask_restplus import Namespace

from app.Controllers.Base import ResponseController
from app.Models.Response import message_response_dto

health_route = Namespace("Health", "Retrieves the health of the server", "/health")


@health_route.route("/")
class HealthController(ResponseController):
    @health_route.response(200, "Healthy", message_response_dto)
    def get(self):
        """Returns a 200 if the API is healthy"""
        return self.ok("yeet")
