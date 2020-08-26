import json
from werkzeug.datastructures import Headers, MultiDict


class MockPostRequest(object):
    def __init__(self, form=None, headers=None, json=None):
        self.headers = Headers(headers)
        self.form = MultiDict(form)
        self.json = json

    def get_json(self, *args, **kwargs):
        return self.json or self.form.to_dict()


def just_log(*args, **kwargs):
    print(json.dumps(args, indent=2))
    print(json.dumps(kwargs, indent=2))
