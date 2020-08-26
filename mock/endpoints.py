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

import time

from flask import Response

TOKEN = '07734'


def __missing_required(d, required):
    return [k for k in required if k not in d]


def __match_all(d, expects):
    for k, v in expects.items():
        if d[k] != v:
            return False
    return True


def handle_auth(request):
    MOCK_USER = 'user@eha.org'
    MOCK_PASSWORD = 'password'

    expected = {'username': MOCK_USER, 'password': MOCK_PASSWORD}
    data = request.get_json(force=True, silent=True)
    if (missing := __missing_required(data, expected.keys())):
        return Response(f'Missing expected data: {missing}', 400)
    if not __match_all(data, expected):
        return Response('Unauthorized', 401)
    return Response(
        {
            MOCK_USER: {
                'session_key': TOKEN,
                'start_time': time.time(),
                'session_length': -1
            }
        },
        200)


def handle_meta(request):
    pass


def handle_data(request):
    pass
