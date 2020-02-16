import json
import uuid
from random import randint

import requests

auth = ""


def test_login():
    data = {
        "email": "ryan.flett@delegator.com.au",
        "password": "B4ckburn3r",
    }
    r = requests.post(
        "http://localhost:5000/account/", headers={"Content-Type": "application/json"}, data=json.dumps(data),
    )
    body = r.json()
    assert r.status_code == 200
    assert "jwt" in body
    global auth
    auth = "Bearer " + body["jwt"]


def test_account_signup():
    data = {
        "org_name": str(uuid.uuid4()),
        "email": f"ryan.flett+apitest{randint(0, 10)}@delegator.com.au",
        "password": "Ap1t3stAccount!",
        "first_name": "Ryan",
        "last_name": "Flett",
        "job_title": "Director",
        "plan_id": "basic",
    }
    r = requests.put(
        "http://localhost:5000/account/", headers={"Content-Type": "application/json"}, data=json.dumps(data),
    )
    assert r.status_code == 200
    assert "url" in r.json()


def test_logout():
    r = requests.delete("http://localhost:5000/account/", headers={"Authorization": auth})
    assert r.status_code == 204


def test_get_active_users():
    r = requests.get("http://localhost:5000/active-users/", headers={"Authorization": auth})
    assert r.status_code == 200


# organisation
def test_get_org():
    r = requests.get("http://localhost:5000/org/", headers={"Authorization": auth})
    assert r.status_code == 200
    assert "org_id" in r.json()
    assert "org_name" in r.json()


def test_update_org():
    data = {
        "org_name": str(uuid.uuid4()),
    }
    r = requests.put(
        "http://localhost:5000/org/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 200
    assert "org_name" in r.json()


def test_get_org_customer_id():
    r = requests.get("http://localhost:5000/org/customer", headers={"Authorization": auth})
    assert r.status_code == 200
    assert "customer_id" in r.json()


def test_get_org_settings():
    r = requests.get("http://localhost:5000/org/settings", headers={"Authorization": auth})
    assert r.status_code == 200
    assert "org_id" in r.json()


# password
def test_reset_password():
    r = requests.delete("http://localhost:5000/password/?email=foo@bar.com")
    assert r.status_code == 204


# roles
def test_get_role():
    r = requests.get("http://localhost:5000/roles/", headers={"Authorization": auth})
    assert r.status_code == 200


# labels
def test_create_label():
    data = {"label": "red", "colour": "red"}
    r = requests.post(
        "http://localhost:5000/task-labels/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_delete_label():
    data = {"label": str(uuid.uuid4()), "colour": "blue"}
    r = requests.post(
        "http://localhost:5000/task-labels/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204
    r = requests.delete("http://localhost:5000/task-labels/2", headers={"Authorization": auth})
    assert r.status_code == 204


def test_update_labels():
    data = {"id": 1, "label": "red label", "colour": "red"}
    r = requests.put(
        "http://localhost:5000/task-labels/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_get_labels():
    r = requests.get("http://localhost:5000/task-labels/", headers={"Authorization": auth})
    assert r.status_code == 200


# types
def test_create_type():
    data = {
        "label": "TestTaskLabel",
        "default_time_estimate": 30,
        "default_priority": 1,
        "default_description": "A description",
        "escalation_policies": [{"display_order": 1, "delay": 600, "from_priority": 1, "to_priority": 2}],
    }
    r = requests.post(
        "http://localhost:5000/task-types/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_delete_type():
    r = requests.delete("http://localhost:5000/task-types/1", headers={"Authorization": auth})  # other (default)
    assert r.status_code == 204


def test_update_type():
    data = {
        "id": 3,
        "label": "My Updated Label",
        "default_time_estimate": 60,
        "default_priority": 0,
        "default_description": "A new description",
        "escalation_policies": [],
    }
    r = requests.put(
        "http://localhost:5000/task-types/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_get_types():
    r = requests.get("http://localhost:5000/task-types/", headers={"Authorization": auth})
    assert r.status_code == 200


# task
def test_create_task():
    data = {
        "type_id": 2,
        "priority": 1,
        "description": "A description",
        "time_estimate": 600,
        "scheduled_for": None,
        "scheduled_notification_period": None,
        "labels": [1],
    }
    r = requests.post(
        "http://localhost:5000/task/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_update_task():
    data = {
        "id": 1,
        "type_id": 2,
        "priority": 0,
        "status": "READY",
        "description": "A new description",
        "time_estimate": 300,
        "labels": [],
    }
    r = requests.put(
        "http://localhost:5000/task/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_schedule_task():
    data = {
        "type_id": 2,
        "priority": 1,
        "description": "A description",
        "time_estimate": 600,
        "scheduled_for": "2021-10-10T10:00:00+1000",
        "scheduled_notification_period": 600,
        "labels": [],
    }
    r = requests.post(
        "http://localhost:5000/task/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_get_task():
    r = requests.get("http://localhost:5000/task/1", headers={"Authorization": auth})
    assert r.status_code == 200


def test_assign_task():
    data = {
        "task_id": 1,
        "assignee": 1,
    }
    r = requests.post(
        "http://localhost:5000/task/assign/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_get_task_activity():
    r = requests.get("http://localhost:5000/task/activity/1", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_transitions():
    r = requests.get("http://localhost:5000/task/transition/", headers={"Authorization": auth})
    assert r.status_code == 200


def test_transition_task():
    data = {
        "task_id": 1,
        "task_status": "IN_PROGRESS",
    }
    r = requests.put(
        "http://localhost:5000/task/transition/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_delay_task():
    data = {"task_id": 1, "delay_for": 1200, "reason": "Because I'm testing it?"}
    r = requests.put(
        "http://localhost:5000/task/delay/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_get_delayed_info():
    r = requests.get("http://localhost:5000/task/delay/1", headers={"Authorization": auth})
    assert r.status_code == 200


def test_drop_task():
    r = requests.post(
        "http://localhost:5000/task/drop/1", headers={"Content-Type": "application/json", "Authorization": auth}
    )
    assert r.status_code == 204


def test_cancel_task():
    r = requests.post(
        "http://localhost:5000/task/cancel/1", headers={"Content-Type": "application/json", "Authorization": auth},
    )
    assert r.status_code == 204


# tasks
def test_get_priorities():
    r = requests.get("http://localhost:5000/tasks/priorities/", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_statuses():
    r = requests.get("http://localhost:5000/tasks/statuses/", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_tasks():
    r = requests.get("http://localhost:5000/tasks/", headers={"Authorization": auth})
    assert r.status_code == 200


# user
def test_get_user_activity():
    r = requests.get("http://localhost:5000/user/activity/1", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_user_pages():
    r = requests.get("http://localhost:5000/user/pages/", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_user_settings():
    r = requests.get("http://localhost:5000/user/settings/", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_user():
    r = requests.get("http://localhost:5000/user/1", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_users():
    r = requests.get("http://localhost:5000/users/", headers={"Authorization": auth})
    assert r.status_code == 200


def test_get_minimal_users():
    r = requests.get("http://localhost:5000/users/minimal", headers={"Authorization": auth})
    assert r.status_code == 200


def test_update_user():
    data = {
        "id": 3,
        "role_id": "DELEGATOR",
        "first_name": "New Name",
        "last_name": "New Name",
        "job_title": "My new title",
    }
    r = requests.put(
        "http://localhost:5000/users/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_disable_user():
    r = requests.post("http://localhost:5000/user/disable/3", headers={"Authorization": auth})
    assert r.status_code == 204


def test_enable_user():
    r = requests.delete("http://localhost:5000/user/disable/3", headers={"Authorization": auth})
    assert r.status_code == 204


def test_delete_user():
    r = requests.delete("http://localhost:5000/user/3", headers={"Authorization": auth})
    assert r.status_code == 204


def test_create_user():
    data = {
        "email": f"ryan.flett+test_user{randint(0, 10)}@delegator.com.au",
        "role_id": "DELEGATOR",
        "first_name": "Ryan",
        "last_name": "Flett",
        "job_title": "Director",
    }
    r = requests.post(
        "http://localhost:5000/users/",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204


def test_resend_welcome():
    data = {"user_id": 6}
    r = requests.post(
        "http://localhost:5000/user/resend-welcome",
        headers={"Content-Type": "application/json", "Authorization": auth},
        data=json.dumps(data),
    )
    assert r.status_code == 204
