import json
import typing

import requests
from dataclasses import dataclass

from faker import Faker

fake = Faker()


@dataclass
class Base:
    url = "http://localhost:5000/"
    headers = {
        "Content-Type": "application/json"
    }
    user_id: int = None
    org_id: int = None
    task_type_id: int = None
    task_id: int = None

    def send(self, method: str, path: str, data: dict = None):
        """Sends an HTTP request"""
        params = {"headers": self.headers}
        if data is not None:
            params = {
                **params,
                "data": json.dumps(data)
            }

        method_mapping = {
            'get': requests.get,
            'delete': requests.delete,
            'put': requests.put,
            'post': requests.post,
            'path': requests.patch
        }

        return method_mapping[method](url=self.url + path, **params)


base = Base()


# Health Check
def test_health():
    r = base.send('get', 'health/')
    assert r.status_code == 200


# Version Check
def test_version():
    r = base.send('get', 'v/')
    assert r.status_code == 200
    assert 'commit_sha' in r.json()


# Signup
def test_signup():
    r = base.send('put', 'account/', data={
        "org_name": "TestOrganisation",
        "email": "test@sink.delegator.com.au",
        "password": "S0meSupersafeP&ssword",
        "first_name": "Test",
        "last_name": "User",
        "job_title": "Lead Tester",
        "plan_id": "basic"
    })
    assert r.status_code == 200
    assert 'url' in r.json()


# Login
def test_login():
    r = base.send('post', 'account/', data={
        "email": "ryan.flett@delegator.com.au",
        "password": "B4ckburn3r"
    })
    assert r.status_code == 200

    # setup values for other tests
    base.headers['Authorization'] = f"Bearer {r.json()['jwt']}"
    base.org_id = r.json()['org_id']
    base.user_id = r.json()['id']


# Roles
def test_get_roles():
    r = base.send('get', 'roles/')
    assert r.status_code == 200
    response_body = r.json()
    assert 'roles' in response_body
    roles = response_body['roles']
    assert len(roles) > 0
    for r in roles:
        assert isinstance(r, dict)
        assert isinstance(r['id'], str)
        assert isinstance(r['rank'], int)
        assert isinstance(r['name'], str)


# Organisation
def test_get_org():
    r = base.send('get', 'org/')
    assert r.status_code == 200
    response_body = r.json()
    assert isinstance(response_body['org_id'], int)
    assert isinstance(response_body['org_name'], str)


def test_get_org_customer_id():
    r = base.send('get', 'org/customer')
    assert r.status_code == 200
    response_body = r.json()
    assert isinstance(response_body['customer_id'], str)


def test_update_org():
    r = base.send('put', 'org/', data={
        "org_id": base.org_id,
        "org_name": "A new organisation name"
    })
    assert r.status_code == 200
    response_body = r.json()
    assert response_body['org_name'] == "A new organisation name"


def test_get_org_settings():
    r = base.send('get', 'org/settings')
    assert r.status_code == 200


# Users
def test_get_active_users():
    r = base.send('get', 'active-users/')
    assert r.status_code == 200
    response_body = r.json()
    assert 'active_users' in response_body
    active_users = response_body['active_users']
    assert len(active_users) > 0
    for au in active_users:
        assert isinstance(au, dict)
        assert isinstance(au['user_id'], int)
        assert isinstance(au['org_id'], int)
        assert isinstance(au['first_name'], str)
        assert isinstance(au['last_name'], str)
        assert isinstance(au['last_active'], str)


# Task Types
def test_create_task_types():
    r = base.send('post', 'task-types/', data={
        "label": "Patient Transport",
        'default_time_estimate': 600,
        'default_description': "A test description",
        'default_priority': 1
    })
    assert r.status_code == 201
    response_body = r.json()
    assert 'id' in response_body
    assert 'label' in response_body
    assert 'org_id' in response_body
    assert 'disabled' in response_body
    assert 'tooltip' in response_body
    assert 'escalation_policies' in response_body
    assert 'default_time_estimate' in response_body
    assert 'default_description' in response_body
    assert 'default_priority' in response_body
    assert response_body['label'] == "Patient Transport"
    base.task_type_id = response_body['id']


def test_update_task_type():
    r = base.send('put', 'task-types/', data={
        "id": base.task_type_id,
        "label": "New Patient Transport",
        'default_time_estimate': 300,
        'default_description': "A new test description",
        'default_priority': 0,
        "escalation_policies": [{
            "display_order": 1,
            "delay": 30,
            "from_priority": 0,
            "to_priority": 1
        }]
    })
    response_body = r.json()
    assert response_body['label'] == "New Patient Transport"
    assert response_body['default_time_estimate'] == 300
    assert response_body['default_description'] == "A new test description"
    assert response_body['default_priority'] == 0
    assert len(response_body['escalation_policies']) == 1
    assert response_body['escalation_policies'][0] == {
        "task_type_id": base.task_type_id,
        "display_order": 1,
        "delay": 30,
        "from_priority": 0,
        "to_priority": 1
    }


def test_disable_task_type():
    r = base.send('delete', f'task-types/{base.task_type_id}')
    assert r.status_code == 200
    assert r.json()['disabled'] is not None


def test_get_task_type():
    r = base.send('get', 'task-types/')
    assert r.status_code == 200
    response_body = r.json()
    assert 'task_types' in response_body
    for _type in response_body['task_types']:
        assert 'id' in _type
        assert 'label' in _type
        assert 'org_id' in _type
        assert 'disabled' in _type
        assert 'tooltip' in _type
        assert 'escalation_policies' in _type


# Tasks
def test_create_task():
    r = base.send('post', 'task/', data={
        "type_id": base.task_type_id,
        "description": "A Task Description",
        "time_estimate": 300,
        "priority": 0
    })
    assert r.status_code == 201
    base.task_id = r.json()['id']


def test_schedule_task():
    r = base.send('post', 'task/', data={
        "type_id": base.task_type_id,
        "description": "A Task Description",
        "scheduled_for": "2020-11-10T15:46:00+10:00",
        "scheduled_notification_period": 300,
        "time_estimate": 300,
        "priority": 0
    })
    assert r.status_code == 201
    response_body = r.json()
    assert response_body['status']['status'] == 'SCHEDULED'


def test_update_task():
    r = base.send('put', 'task/', data={
        "id": base.task_id,
        "type_id": base.task_type_id,
        "description": "A New Task Description",
        "status": "READY",
        "time_estimate": 300,
        "priority": 0
    })
    assert r.status_code == 200
    assert r.json()['description'] == "A New Task Description"


def test_get_tasks():
    r = base.send('get', 'tasks/')
    assert r.status_code == 200
    response_body = r.json()
    assert 'tasks' in response_body
    assert len(response_body['tasks']) > 0


def test_get_task():
    r = base.send('get', f'task/{base.task_id}')
    assert r.status_code == 200
    response_body = r.json()
    assert response_body['id'] == base.task_id


def test_get_task_priorities():
    r = base.send('get', 'tasks/priorities/')
    assert r.status_code == 200
    response_body = r.json()
    assert 'priorities' in response_body
    assert len(response_body['priorities']) == 3
    for p in response_body['priorities']:
        assert isinstance(p['priority'], int)
        assert isinstance(p['label'], str)


def test_get_task_statuses():
    r = base.send('get', 'tasks/statuses/')
    assert r.status_code == 200
    response_body = r.json()
    assert 'statuses' in response_body
    assert len(response_body['statuses']) == 4
    for s in response_body['statuses']:
        assert isinstance(s['status'], str)
        assert isinstance(s['label'], str)
        assert isinstance(s['disabled'], bool)
        assert isinstance(s['tooltip'], str) or s['tooltip'] is None


# Task Actions
def test_assign_task():
    r = base.send('post', 'task/assign/', data={
        "task_id": base.task_id,
        "assignee": base.user_id
    })
    assert r.status_code == 200
    response_body = r.json()
    assert 'assignee' in response_body
    assert response_body['assignee']['id'] == base.user_id


def test_get_available_transitions():
    r = base.send('get', f'task/transition/{base.task_id}')
    assert r.status_code == 200
    response_body = r.json()
    assert 'statuses' in response_body
    assert len(response_body['statuses']) > 0


def transition_task():
    r = base.send('put', 'task/transition', data={
        "task_id": base.task_id,
        "task_status": "IN_PROGRESS"
    })
    assert r.status_code == 200
    response_body = r.json()
    assert response_body['status']['status'] == 'IN_PROGRESS'


def test_delay_task():
    r = base.send('put', 'task/delay/', data={
        "task_id": base.task_id,
        "delay_for": 20,
        "reason": "A test delay"
    })
    assert r.status_code == 200
    response_body = r.json()
    assert response_body['status']['status'] == 'DELAYED'


def test_get_delayed_info():
    r = base.send('get', f'task/delay/{base.task_id}')
    assert r.status_code == 200
    response_body = r.json()
    assert "task_id" in response_body
    assert "delay_for" in response_body
    assert "delayed_at" in response_body
    assert "delayed_by" in response_body
    assert "reason" in response_body
    assert "snoozed" in response_body
    assert "expired" in response_body
    assert response_body["reason"] == "A test delay"


def test_drop_task():
    r = base.send('post', f'task/drop/{base.task_id}')
    assert r.status_code == 200
    response_body = r.json()
    assert response_body['assignee'] is None
    assert response_body['status']['status'] == 'READY'


def test_cancel_task():
    r = base.send('post', f'task/cancel/{base.task_id}')
    assert r.status_code == 200
    response_body = r.json()
    assert response_body['status']['status'] == 'CANCELLED'


# Task Labels
def test_create_labels():
    create_data = {
        "labels": [
            {
                "label": "labelOne",
                "colour": "red"
            },
            {
                "label": "labelTwo",
                "colour": "green"
            },
            {
                "label": "labelThree",
                "colour": "yellow"
            }
        ]
    }
    r = base.send('post', 'task-labels/', create_data)
    assert r.status_code == 200
    response_body = r.json()
    assert 'labels' in response_body
    assert len(response_body['labels']) == 3
    for label in response_body['labels']:
        assert isinstance(label['id'], int)
        assert isinstance(label['label'], str)
        assert isinstance(label['colour'], str)


def test_create_task_with_labels():
    r = base.send('post', 'task/', data={
        "type_id": base.task_type_id,
        "description": "A Task Description",
        "time_estimate": 300,
        "priority": 0,
        "labels": [1, 2, 3]
    })
    assert r.status_code == 201
    response_body = r.json()
    assert 'labels' in response_body
    assert len(response_body['labels']) == 3


def test_schedule_task_with_labels():
    r = base.send('post', 'task/', data={
        "type_id": base.task_type_id,
        "description": "A Task Description",
        "scheduled_for": "2020-11-10T15:46:00+10:00",
        "scheduled_notification_period": 300,
        "time_estimate": 300,
        "priority": 0,
        "labels": [1]
    })
    assert r.status_code == 201
    response_body = r.json()
    assert response_body['status']['status'] == 'SCHEDULED'
    assert 'labels' in response_body
    assert len(response_body['labels']) == 1
    assert response_body['labels'][0] == {
        "id": 1,
        "label": "labelOne",
        "colour": "red"
    }


def test_delete_label():
    delete_data = {
        "labels": [
            {
                "id": 1,
                "label": "labelOne",
                "colour": "red"
            }
        ]
    }
    r = base.send('post', 'task-labels/', delete_data)
    assert r.status_code == 200
    response_body = r.json()
    assert 'labels' in response_body
    assert len(response_body['labels']) == 1
    for label in response_body['labels']:
        assert isinstance(label['id'], int)
        assert isinstance(label['label'], str)
        assert isinstance(label['colour'], str)


def test_update_label():
    update_data = {
        "labels": [
            {
                "id": 1,
                "label": "labelOneNew",
                "colour": "blue"
            }
        ]
    }
    r = base.send('post', 'task-labels/', update_data)
    assert r.status_code == 200
    response_body = r.json()
    assert 'labels' in response_body
    assert len(response_body['labels']) == 1
    assert response_body['labels'][0] == {
        "id": 1,
        "label": "labelOneNew",
        "colour": "blue"
    }


# User Activity Controller
def test_user_activity():
    response = base.send("get", f"user/activity/{base.user_id}")
    assert response.status_code == 200
    # Activity will change so as long as 200 comes back it's okay


# User Pages Controller
def test_user_pages():
    response = base.send("get", "user/pages")
    assert response.status_code == 200
    # Which pages user can see doesn't matter too much


# Users Controller
def test_get_users():
    response = base.send("get", "users/")
    assert response.status_code == 200
    response_body: typing.List = response.json()
    assert len(response_body) > 0


def test_create_user():
    create_data = {
        "email": fake.email(),
        "first_name": fake.name(),
        "last_name": fake.name(),
        "role_id": "USER",
        "job_title": fake.bs(),
        "disabled": None
    }
    response = base.send("post", "users/", create_data)
    assert response.status_code == 201
    response_body = response.json()
    assert response_body["email"] == create_data["email"]


def test_update_user():
    update_data = {
        "id": base.user_id,
        "first_name": fake.name(),
        "last_name": fake.name(),
        "role_id": "MANAGER",
        "job_title": fake.bs(),
        "disabled": None
    }
    # Check how to update without state
    response = base.send("put", "users/", update_data)
    assert response.status_code == 200


# User Settings Controller
def test_get_user_settings():
    response = base.send("get", "user/settings")
    assert response.status_code == 200
    response_body = response.json()
    assert response_body["user_id"] == base.user_id


def test_update_user_settings():
    update_data = {
        "tz_offset": "+0900"
    }
    response = base.send("put", "user/settings", update_data)
    assert response.status_code == 200
    response_body = response.json()
    assert response_body["tz_offset"] == update_data["tz_offset"]


# User Controller
def test_user_get():
    response = base.send("get", f"user/{base.user_id}")
    assert response.status_code == 200
    response_body = response.json()
    assert response_body['id'] == base.user_id


def test_user_delete():
    response = base.send("delete", f"user/{base.user_id}")
    assert response.status_code == 204
