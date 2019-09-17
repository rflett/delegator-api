import json
import pytest
import requests
from dataclasses import dataclass


@dataclass
class Base:
    url = "http://localhost:5000/"
    headers = {
        "Content-Type": "application/json"
    }
    user_id: int = None
    org_id: int = None
    task_type_id: int = None

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
# TODO enable after subscription API has /customer endpoint
# def test_signup():
#     r = base.send('put', 'account/', data={
#         "org_name": "TestOrganisation",
#         "email": "test@sink.delegator.com.au",
#         "password": "S0meSupersafeP&ssword",
#         "first_name": "Test",
#         "last_name": "User",
#         "job_title": "Lead Tester",
#         "plan_id": "basic"
#     })
#     assert r.status_code == 200
#     assert 'url' in r.json()


# Login
def test_login():
    r = base.send('post', 'account/', data={
        "email": "ryan.flett@frontburner.com.au",
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
    r = base.send('post', 'tasks/types/', data={
        "label": "Patient Transport"
    })
    assert r.status_code == 201
    response_body = r.json()
    assert 'id' in response_body
    assert 'label' in response_body
    assert 'org_id' in response_body
    assert 'disabled' in response_body
    assert 'tooltip' in response_body
    assert 'escalation_policies' in response_body
    assert response_body['label'] == "Patient Transport"
    base.task_type_id = response_body['id']


def test_update_task_type():
    r = base.send('put', 'tasks/types/', data={
        "id": base.task_type_id,
        "label": "New Patient Transport",
        "escalation_policies": [{
            "display_order": 1,
            "delay": 30,
            "from_priority": 0,
            "to_priority": 1
        }]
    })
    response_body = r.json()
    assert response_body['label'] == "New Patient Transport"
    assert len(response_body['escalation_policies']) == 1
    assert response_body['escalation_policies'][0] == {
        "task_type_id": base.task_type_id,
        "display_order": 1,
        "delay": 30,
        "from_priority": 0,
        "to_priority": 1
    }


def test_disable_task_type():
    r = base.send('delete', 'tasks/types/', data={
        "id": base.task_type_id
    })
    assert r.status_code == 200
    assert r.json()['disabled'] is not None


def test_get_task_type():
    r = base.send('get', 'tasks/types/')
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
