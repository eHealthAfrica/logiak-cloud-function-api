#!/usr/bin/env python

# Copyright (C) 2020 by eHealth Africa : http://www.eHealthAfrica.org
#
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the "License");
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

import pytest


from test.app.mock import endpoints

from . import AuthHeaders, MockPostRequest  # noqa (fixtures import strangely)


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
        assert(res.data is not None), res.data


@pytest.mark.parametrize('path,headers,code', [
    (
        '/',
        {'uname': 'a', 'password': 'password'},
        400),
    (
        '/',
        {'Logiak-User-Id': endpoints.MOCK_USER, 'Logiak-Session-Key': 'bad-token'},
        401),
    (
        '/',
        {'Logiak-User-Id': endpoints.MOCK_USER, 'Logiak-Session-Key': endpoints.TOKEN},
        200)
])
@pytest.mark.unit
def test__require_auth(path, headers, code):
    request = MockPostRequest(path=path, headers=headers)
    res = endpoints.handle_no_op(request)
    assert(res.status_code == code), res.data
    if code == 200:
        assert(res.data is not None), res.data


@pytest.mark.parametrize('path,code', [
    (
        '/app',
        200),
    (
        '/app/0.2.4/en',
        200),
    (
        '/moota',
        404),
    (
        '/meta/app',
        200),
    (
        '/meta/something',
        404),
    (
        '/meta/app/0.2.4/en',
        200),
    (
        '/meta/app/still/valid',
        200),
    (
        '/meta/schema/0.2.4',
        200),
    (
        '/meta/schema/0.2.4/missing',
        404),
    (
        '/meta/schema/9.9.9/allocation',
        200)
])
def test__meta(path, code, AuthHeaders):  # noqa
    request = MockPostRequest(path=path, headers=AuthHeaders)
    res = endpoints.handle_meta(request)
    assert(res.status_code == code), res.data
    if code == 200:
        assert(res.data is not None), res.data


@pytest.mark.parametrize('path,code', [
    (
        '/data',
        404),
    (
        '/data/allocation/not-supported',
        404),
    (
        '/data/something',
        404),
    (
        '/data/allocation/query',
        200),
    (
        '/data/batch/query',
        200),
    (
        '/data/missing-type/query',
        404),
    (
        '/allocation/query',
        200),
])
def test__data(path, code, AuthHeaders):  # noqa
    request = MockPostRequest(path=path, headers=AuthHeaders)
    res = endpoints.handle_data(request)
    assert(res.status_code == code), res.data
    if code == 200:
        assert(res.data is not None), res.data
