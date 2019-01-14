from app.Models import User
from app.Models.Enums import UserRole


def test_user_as_dict():
    user = User(
        org_id=1,
        username='flett',
        email='ryan@flett.com',
        first_name='ryan',
        last_name='flett',
        password='password',
        role=UserRole.ADMIN
    )
    expected = {
        'org_id': 1,
        'username': 'flett',
        'email': 'ryan@flett.com',
        'first_name': 'ryan',
        'last_name': 'flett',
        'password': 'password',
        'role': 'admin'
    }
    actual = user.as_dict()
    assert expected == actual
