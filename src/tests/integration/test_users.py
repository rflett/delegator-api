import json
import os
import pytest
import requests
from dataclasses import dataclass


@dataclass()
class Base:

    if os.getenv('APP_ENV') == 'Ci':
        url = "http://127.0.0.1:5000/"
    else:
        url = "http://localhost:5000/"

    headers = {
        "Content-Type": "application/json"
    }
    user_id: int = None

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
            'post': requests.post
        }

        return method_mapping[method](url=self.url + path, **params)


base = Base()

# Login
@pytest.mark.run('first')
def test_bad_email_login():
    r = base.send('post', 'login', data={
        "email": "XXX@XXX.com",
        "password": "B4ckburn3r"
    })
    assert r.status_code == 401


@pytest.mark.run(after='test_bad_email_login')
def test_bad_password_login():
    r = base.send('post', 'login', data={
        "email": "ryan.flett@frontburner.com.au",
        "password": "BADPASSWORD!@1234"
    })
    assert r.status_code == 401


@pytest.mark.run(after='test_bad_password_login')
def test_login():
    r = base.send('post', 'login', data={
        "email": "ryan.flett@frontburner.com.au",
        "password": "B4ckburn3r"
    })
    assert r.status_code == 200

    _jwt = r.json()['jwt']
    assert isinstance(_jwt, str)

    # setup jwt for other tests
    base.headers['Authorization'] = f"Bearer {_jwt}"


# Roles
@pytest.mark.run(after='test_login')
def test_get_roles():
    r = base.send('get', 'roles')
    assert r.status_code == 200
    roles = r.json()
    assert len(roles) > 0
    for r in roles:
        assert isinstance(r, dict)
        assert isinstance(r['id'], str)
        assert isinstance(r['rank'], int)
        assert isinstance(r['name'], str)


# Users
@pytest.mark.run(after='test_login')
def test_create_user_already_exists():
    r = base.send('post', 'users', data={
        "email": "ryan.flett@frontburner.com.au",
        "first_name": "James",
        "last_name": "Turner",
        "role_id": "USER",
        "job_title": "Developer"
    })
    assert r.status_code == 400


@pytest.mark.run(after='test_login')
def test_create_user_missing_details():
    r = base.send('post', 'users', data={
        "email": "james@backburner.com.au"
    })
    assert r.status_code == 400


@pytest.mark.run(after='test_create_user_missing_details')
def test_create_user():
    r = base.send('post', 'users', data={
        "email": "james@backburner.com.au",
        "first_name": "James",
        "last_name": "Turner",
        "role_id": "USER",
        "job_title": "Developer"
    })
    assert r.status_code == 201
    assert isinstance(r.json()['id'], int)
    base.user_id = r.json()['id']


@pytest.mark.run(after='test_create_user')
def test_get_user():
    r = base.send('get', f'user/{base.user_id}')
    assert r.status_code == 200


@pytest.mark.run(after='test_create_user')
def test_get_user_not_exists():
    r = base.send('get', 'user/999')
    assert r.status_code == 404


@pytest.mark.run(after='test_create_user')
def test_update_user_not_disabled():
    r = base.send('put', 'users', data={
        "id": base.user_id,
        "email": "james@backburner.com",
        "first_name": "James",
        "last_name": "W. Turner",
        "role_id": "MANAGER",
        "job_title": "Promoted from Scrub"
    })
    assert r.status_code == 200
    assert r.json()['disabled'] is None


@pytest.mark.run(after='test_create_user')
def test_update_user_disabled():
    r = base.send('put', 'users', data={
        "id": base.user_id,
        "email": "james@backburner.com",
        "first_name": "James",
        "last_name": "W. Turner",
        "role_id": "MANAGER",
        "job_title": "Promoted from Scrub",
        "disabled": "2019-08-29T23:00:00.0000Z"
    })
    assert r.status_code == 200
    assert r.json()['disabled'] is not None


@pytest.mark.run(after='test_create_user')
def test_update_user_bad_disabled():
    r = base.send('put', 'users', data={
        "id": base.user_id,
        "disabled": "i am not a date"
    })
    assert r.status_code == 400


@pytest.mark.run(after='test_create_user')
def test_update_user_bad_first_name():
    r = base.send('put', 'users', data={
        "id": base.user_id,
        "first_name": 1,
    })
    assert r.status_code == 400


@pytest.mark.run(after='test_create_user')
def test_update_user_bad_last_name():
    r = base.send('put', 'users', data={
        "id": base.user_id,
        "last_name": True,
    })
    assert r.status_code == 400


@pytest.mark.run(after='test_create_user')
def test_update_user_bad_role_id():
    r = base.send('put', 'users', data={
        "id": base.user_id,
        "role_id": "FOOEY",
    })
    assert r.status_code == 400


@pytest.mark.run(after='test_create_user')
def test_update_user_bad_job_title():
    r = base.send('put', 'users', data={
        "id": base.user_id,
        "job_title": "",
    })
    assert r.status_code == 400


@pytest.mark.run(after='test_create_user')
def test_get_user_activity():
    r = base.send('get', f'user/activity/{base.user_id}')
    assert r.status_code == 200


@pytest.mark.run(after='test_create_user')
def test_get_user_activity_user_not_exist():
    r = base.send('get', 'user/activity/999')
    assert r.status_code == 404


@pytest.mark.run(after='test_create_user')
def test_get_users():
    r = base.send('get', 'users')
    assert r.status_code == 200
    users = r.json()
    assert len(users) > 0
    for u in users:
        assert isinstance(u, dict)
        assert isinstance(u['id'], int)
        assert isinstance(u['org_id'], int)
        assert isinstance(u['email'], str)
        assert isinstance(u['first_name'], str)
        assert isinstance(u['last_name'], str)
        assert isinstance(u['role'], dict)
        assert isinstance(u['job_title'], str)
        assert isinstance(u['created_at'], str)
        assert isinstance(u['created_by'], str)
        assert isinstance(u['updated_at'], str)


@pytest.mark.run(after='test_create_user')
def test_get_active_users():
    r = base.send('get', 'users/active')
    assert r.status_code == 200
    active_users = r.json()
    assert len(active_users) > 0
    for u in active_users:
        assert isinstance(u, dict)
        assert isinstance(u['user_id'], int)
        assert isinstance(u['org_id'], int)
        assert isinstance(u['first_name'], str)
        assert isinstance(u['last_name'], str)
        assert isinstance(u['last_active'], str)


@pytest.mark.run(after='test_create_user')
def test_get_pages():
    r = base.send('get', 'user/pages')
    assert r.status_code == 200
    pages = r.json()
    assert len(pages) > 0
    for p in pages:
        assert isinstance(p, str)


@pytest.mark.run(after='test_create_user')
def test_delete_user_not_exists():
    r = base.send('delete', 'user/999')
    assert r.status_code == 404


@pytest.mark.run('last')
def test_delete_user():
    r = base.send('delete', f'user/{base.user_id}')
    assert r.status_code == 204
