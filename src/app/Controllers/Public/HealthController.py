from flask_restx import Namespace, Resource, fields

api = Namespace(path="/health", name="Health", description="Check API health")


@api.route("/")
class Health(Resource):
    @api.marshal_with(api.model("Health Response", {"msg": fields.String()}), code=200)
    def get(self, **kwargs):
        """Returns a 200 if the API is healthy"""
        return {"msg": "I return, therefore I am healthy"}, 200
