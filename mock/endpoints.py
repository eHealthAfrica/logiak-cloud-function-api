#!/usr/bin/env python

# Copyright (C) 2020 by eHealth Africa : http://www.eHealthAfrica.org
#
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
from functools import wraps
import json
import time

from flask import jsonify, make_response, Response
from spavro.schema import parse

if os.environ.get('TEST', False):
    PATH = os.getcwd() + '/app/mock'
else:
    PATH = os.getcwd() + '/mock'

# fake credentials
MOCK_USER = 'user@eha.org'
MOCK_PASSWORD = 'password'
TOKEN = '07734'

# fake data
MOCK_PROJECT = f'{PATH}/lomis'
META_FOLDER = f'{MOCK_PROJECT}/meta'
DATA_FOLDER = f'{MOCK_PROJECT}/data'
SCHEMAS = {}
DATA = []

with open(f'{META_FOLDER}/app-info.json') as f:
    APP_INFO = json.load(f)
with open(f'{META_FOLDER}/app.json') as f:
    APP = json.load(f)
with open(f'{META_FOLDER}/schemas.json') as f:
    SCHEMA_OBJ = json.load(f)
    for name, s in SCHEMA_OBJ.items():
        SCHEMAS[name] = parse(s)
with open(f'{DATA_FOLDER}/data.json') as f:
    DATA = json.load(f)


# helpers

def __missing_required(d, required):
    if not d:
        return required
    return [k for k in required if k not in d]


def __match_all(d, expects):
    for k, v in expects.items():
        if d[k] != v:
            return False
    return True


# decorators

def require_auth(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        headers = dict(request.headers)
        print(headers)
        required = {
            'Logiak-User-Id': MOCK_USER,
            'Logiak-Session-Key': TOKEN
        }
        if (missing := __missing_required(headers, required.keys())):  # noqa
            return Response(f'Missing required headers: {missing}', 400)
        if not __match_all(headers, required):
            return Response('Bad Credentials', 401)
        return fn(request, *args, **kwargs)
    return wrapper


# actual request handlers

def handle_auth(request):
    expected = {'username': MOCK_USER, 'password': MOCK_PASSWORD}
    data = request.get_json(force=True, silent=True)
    if (missing := __missing_required(data, expected.keys())):
        return Response(f'Missing expected data: {missing}', 400)
    if not __match_all(data, expected):
        return Response('Unauthorized', 401)
    return Response(
        json.dumps({
            MOCK_USER: {
                'session_key': TOKEN,
                'start_time': time.time(),
                'session_length': -1
            }
        }),
        200,
        mimetype='application/json')


@require_auth
def handle_no_op(request):
    return Response('', 200)


def __meta_info():
    return Response(json.dumps(APP_INFO), 200, mimetype='application/json')


def __meta_list_schemas():
    return Response(
        json.dumps([k for k in SCHEMA_OBJ]),
        200,
        mimetype='application/json'
    )


def __meta_schema(name):
    try:
        return Response(
            json.dumps(SCHEMA_OBJ[name]), 200, mimetype='application/json')
    except KeyError:
        return Response(f'schema : {name} not found', 404)


def __meta_app():
    return Response(json.dumps(APP), 200, mimetype='application/json')


@require_auth
def handle_meta(request):
    try:
        path = request.path.split('/')[1:]
    except Exception:
        return Response('Not Found', 404)
    if path[0] == 'meta' and len(path) == 1:
        return __meta_info()
    elif len(path) == 1:
        return Response('Not Found', 404)
    elif path[1] == 'schema':
        if len(path) == 3:
            return __meta_list_schemas()
        if len(path) == 4:
            return __meta_schema(path[3])
    elif path[1] == 'app':
        return __meta_app()
    return Response(f'Not Found @ {path}', 404)


def __data_all(name):
    if name not in DATA:
        raise KeyError
    yield "["
    for i in DATA[name]:
        yield json.dumps(i) + ','
    yield "]"


@require_auth
def handle_data(request):
    try:
        path = request.path.split('/')[1:]
    except Exception:
        return Response('Not Found', 404)
    try:
        if path[2] == 'query':
            name = path[1]
            if name in DATA:  # keyError from Generator was causing problems
                return Response(
                    __data_all(path[1]),
                    200,
                    mimetype='application/json')
    except Exception:
        pass
    return Response('Not Found', 404)
