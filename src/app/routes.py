from app import app
from flask import Response, request
from app.Controllers import AuthController


@app.route('/login', methods=['POST'])
def index():
    return AuthController.login(request.get_json())


@app.route('/health')
def health():
    return Response(status=200)
