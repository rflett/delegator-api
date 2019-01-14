import json
from app import app
from flask import Response
from app.Controllers import UserController, OrganisationController
from app.Models.Enums import UserRole


@app.route('/')
def index():
    OrganisationController.create_org("new_org")
    org = OrganisationController.get_org_by_name("new_org")

    UserController.create_user(
        org_id=org.id,
        username="fletty",
        email="ryan.flett1@gmail.com",
        first_name="Ryan",
        last_name="Flett",
        password="supersecretpassword",
        role=UserRole.ADMIN
    )
    user = UserController.get_user_by_username('fletty')
    return json.dumps(user.as_dict())


@app.route('/health')
def health():
    return Response(status=200)
