import pytest


from test.app.mock import endpoints

from . import MockPostRequest


@pytest.mark.parametrize('post_contents,code', [
    ({'username': 'a', 'password': 'password'}, 200)
])
@pytest.mark.unit
def test__auth(post_contents, code):
    request = MockPostRequest(post_contents)
    res = endpoints.handle_auth(request)
    assert(res.status_code == code)
