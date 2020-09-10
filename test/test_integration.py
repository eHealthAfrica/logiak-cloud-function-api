#!/usr/bin/env python

# Copyright (C) 2018 by eHealth Africa : http://www.eHealthAfrica.org
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

from flask import Response
import json
import os
import pytest


from test.app.cloud import meta, data, auth

from test.app.cloud.auth import require_auth
from test.app.cloud.utils import escape_email

from . import (  # noqa
    LOG,
    check_local_firebase_readyness,
    cfs,
    rtdb,
    fb_app,
    MockAuthHandler,
    MockPostRequest,
    rtdb_options,
    sample_project,
    TestSession
)


TEST_USER = 'aboubacar.douno@ehealthnigeria.org'
TEST_APP_VERSION = '0.0.42'
TEST_APP_LANG = 'en'
TEST_OBJECT_TYPE = 'batch'
TEST_OWNED_OF_TYPE = 5


@pytest.mark.integration
def test__setup_emulator(sample_project):  # noqa  # import static -> emulator
    assert(True)


@pytest.mark.integration
def test__auth_has_app(MockAuthHandler):  # noqa
    assert(MockAuthHandler.sign_in_with_email_and_password('a', 'b') is True)


# AUTH

@pytest.mark.parametrize('email,res', [
    (
        TEST_USER,
        True),
    (
        'fake.person@ehealthnigeria.org',
        False)
])
@pytest.mark.integration
def test__auth_has_app(MockAuthHandler, email, res):  # noqa
    assert(MockAuthHandler.user_has_app_access(email) is res)


@pytest.mark.parametrize('body,code', [
    (
        {
            "username": TEST_USER
        },
        400),
    (
        {
            "username": "bad-user",
            "password": "password"
        },
        401),
    (
        {
            "username": TEST_USER,
            "password": "a-fake-password"
        },
        200)
])
@pytest.mark.integration
def test__auth_events(MockAuthHandler, body, code):  # noqa
    res = auth.auth_request(body, MockAuthHandler)
    assert(res.status_code == code)


@pytest.mark.integration
def test__session(MockAuthHandler, rtdb):  # noqa
    session = MockAuthHandler.create_session(TEST_USER)
    assert(TEST_USER in session)
    session = session[TEST_USER]
    session_key = session['session_key']
    assert(MockAuthHandler._session_is_valid(session))
    assert(MockAuthHandler.verify_session(TEST_USER, session_key))

    # invalidate the token
    key = escape_email(TEST_USER)
    session_obj_ref = f'{MockAuthHandler.session_path}/{key}/{session_key}'
    expiry_ref = f'{session_obj_ref}/session_length'
    rtdb.reference(expiry_ref).set(0)
    assert(MockAuthHandler.verify_session(TEST_USER, session_key) is False)
    MockAuthHandler._remove_expired_sessions(TEST_USER)
    assert(rtdb.reference(session_obj_ref).get() is None)


@pytest.mark.integration
def test__bad_session(MockAuthHandler, rtdb):  # noqa
    assert(MockAuthHandler.verify_session('bad-user', 'bad-token') is False)
    MockAuthHandler._remove_expired_sessions('bad-user')
    assert(MockAuthHandler._session_is_valid({'a': 'bad_session'}) is False)


@pytest.mark.integration
def test__require_auth(MockAuthHandler, TestSession):  # noqa

    @require_auth(MockAuthHandler)
    def _fn(*args, **kwargs):
        return True

    session = TestSession(TEST_USER)
    session_key = session[TEST_USER]['session_key']
    good_headers = {'Logiak-User-Id': TEST_USER, 'Logiak-Session-Key': session_key}
    request = MockPostRequest(headers=good_headers)
    assert(_fn(request) is True)

    bad_headers = {'Logiak-User-Id': TEST_USER, 'Logiak-Session-Key': 'bad-key'}
    request = MockPostRequest(headers=bad_headers)
    res = _fn(request)
    assert(isinstance(res, Response))
    assert(res.status_code == 401)

    bad_headers = {'Missing ID': TEST_USER, 'Logiak-Session-Key': 'bad-key'}
    request = MockPostRequest(headers=bad_headers)
    res = _fn(request)
    assert(isinstance(res, Response))
    assert(res.status_code == 400)


# META

@pytest.mark.parametrize('path,status_code', [
    (
        'meta/app',
        200),
    (
        f'meta/app/{TEST_APP_VERSION}/{TEST_APP_LANG}',
        200),
    (
        f'meta/schema/{TEST_APP_VERSION}',
        200),
    (
        f'meta/schema/{TEST_APP_VERSION}/{TEST_OBJECT_TYPE}',
        200),
    (
        'meta/missing',
        404),
    (
        f'meta/app/0.22511/{TEST_APP_LANG}',
        404),
    (
        'meta/schema/0.22511',
        404),
    (
        f'meta/schema/{TEST_APP_VERSION}/missing',
        404)
])
@pytest.mark.integration
def test__meta_resolution(rtdb, path, status_code):  # noqa
    res = meta.resolve(path.split('/'), rtdb)
    assert(res.status_code == status_code)


@pytest.mark.integration
def test__meta_info(rtdb):  # noqa
    res = meta._meta_info(rtdb)
    assert(res is not None)
    assert(res['uuid'] == os.environ.get('LOGIAK_APP_ID'))


@pytest.mark.integration
def test__meta_app(rtdb):  # noqa
    res = meta._meta_app(rtdb, TEST_APP_VERSION, TEST_APP_LANG)
    assert(res is not None)
    assert(isinstance(res, dict))
    assert('projectUuid' in res.keys()), json.dumps(res, indent=2)


@pytest.mark.integration
def test__meta_list_schemas(rtdb):  # noqa
    res = meta._meta_list_schemas(rtdb, TEST_APP_VERSION)
    assert(res is not None)
    assert(isinstance(res, list))
    assert(TEST_OBJECT_TYPE in res)


@pytest.mark.integration
def test__meta_get_schema(rtdb):  # noqa
    res = meta._meta_schema(rtdb, TEST_APP_VERSION, TEST_OBJECT_TYPE)
    assert(res is not None)
    assert(isinstance(res, dict))
    assert('name' in res.keys())


# DATA

@pytest.mark.integration
def test__data_eligible_docs(cfs):  # noqa
    assert(
        len(data._eligible_docs(
            cfs,
            TEST_USER,
            TEST_OBJECT_TYPE)) == TEST_OWNED_OF_TYPE)


@pytest.mark.integration
def test__data_eligible_doc(cfs):  # noqa
    _ids = data._eligible_docs(
        cfs,
        TEST_USER,
        TEST_OBJECT_TYPE)
    _id = _ids[0]
    assert(data._is_eligible(
        cfs,
        TEST_USER,
        TEST_OBJECT_TYPE,
        _id))


@pytest.mark.integration
def test__data_get_single_doc(cfs):  # noqa
    _ids = data._eligible_docs(
        cfs,
        TEST_USER,
        TEST_OBJECT_TYPE)
    _id = _ids[0]
    _doc = data._get(
        cfs,
        TEST_USER,
        TEST_OBJECT_TYPE,
        _id)
    doc = json.loads(_doc)
    assert(doc['uuid'] in _ids)


@pytest.mark.integration
def test__data_dont_get_bad_doc(cfs):  # noqa
    _ids = data._eligible_docs(
        cfs,
        TEST_USER,
        TEST_OBJECT_TYPE)
    _id = _ids[0]
    _doc = data._get(
        cfs,
        'bad-user',
        TEST_OBJECT_TYPE,
        _id)
    assert(_doc is None)


@pytest.mark.integration
def test__data_query_no_filter(cfs):  # noqa
    _gen = data._query(
        cfs,
        TEST_USER,
        TEST_OBJECT_TYPE,
        {})
    # read it as Flask will report it
    res = ''.join(_gen)
    _docs = json.loads(res)
    # make sure only allowed docs were returned
    allowed_ids = data._eligible_docs(
        cfs,
        TEST_USER,
        TEST_OBJECT_TYPE)
    assert(
        all([(i.get('uuid') in allowed_ids) for i in _docs])
    )


@pytest.mark.integration
def test__data_query_no_matches(cfs):  # noqa
    _gen = data._query(
        cfs,
        'bad-user',
        TEST_OBJECT_TYPE,
        {})
    # read it as Flask will report it
    res = ''.join(_gen)
    _docs = json.loads(res)
    # make sure only allowed docs were returned
    assert(
        _docs == []
    )


# @pytest.mark.integration
# def test__data_(cfs):  # noqa
#     pass
