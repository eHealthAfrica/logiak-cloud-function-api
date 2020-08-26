import json
import pytest
from werkzeug.datastructures import Headers, MultiDict


from test.app.mock import endpoints


@pytest.fixture(scope='function')
def AuthHeaders():
    return {
        'Logiak-User-Id': endpoints.MOCK_USER, 'Logiak-Session-Key': endpoints.TOKEN
    }


class MockPostRequest(object):
    def __init__(self, path='/', form=None, headers=None, json=None):
        self.headers = Headers(headers)
        self.form = MultiDict(form)
        self.json = json
        self.path = path

    def get_json(self, *args, **kwargs):
        return self.json or self.form.to_dict()


def just_log(*args, **kwargs):
    print(json.dumps(args, indent=2))
    print(json.dumps(kwargs, indent=2))
