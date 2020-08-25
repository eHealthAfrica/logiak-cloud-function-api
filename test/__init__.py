import json
from werkzeug.datastructures import MultiDict


class MockPostRequest(object):
    def __init__(self, contents):
        self.form = MultiDict(contents)


def just_log(*args, **kwargs):
    print(json.dumps(args, indent=2))
    print(json.dumps(kwargs, indent=2))
