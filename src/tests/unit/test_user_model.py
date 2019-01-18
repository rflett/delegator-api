from app.Models import User


def test_user_as_dict():
    user = User(
        org_id=1,
        username='flett',
        email='ryan@flett.com',
        first_name='ryan',
        last_name='flett',
        password='password'
    )
    expected = {
        'org_id': 1,
        'username': 'flett',
        'email': 'ryan@flett.com',
        'first_name': 'ryan',
        'last_name': 'flett',
        'password': 'password'
    }
    actual = user.as_dict()
    assert expected == actual
