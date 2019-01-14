from app.Models import Organisation


def test_org_as_dict():
    org = Organisation(
        name="etemt"
    )
    expected = {
        'name': 'etemt'
    }
    actual = org.as_dict()
    assert expected == actual
