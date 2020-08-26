import pytest


from test.app.mock import endpoints

from . import MockPostRequest


@pytest.mark.parametrize('form,headers,json,code', [
    (
        {'uname': 'a', 'password': 'password'},
        {},
        {},
        400),
    (
        {'username': 'a', 'password': 'password'},
        {},
        {},
        401),
    (
        {'username': 'user@eha.org', 'password': 'password'},
        {},
        {},
        200),
    (
        {},
        {},
        {'username': 'user@eha.org', 'password': 'password'},
        200),
])
@pytest.mark.unit
def test__auth(form, headers, json, code):
    request = MockPostRequest(form=form, headers=headers, json=json)
    res = endpoints.handle_auth(request)
    assert(res.status_code == code), res.data
    if code == 200:
        print(res.data)
        assert(res.data is not None), res.data
