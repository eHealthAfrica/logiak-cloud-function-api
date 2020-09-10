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


import logging
import json
import os
import pytest
from time import sleep
from unittest.mock import patch
from werkzeug.datastructures import Headers, MultiDict


import firebase_admin
import firebase_admin.credentials
from firebase_admin.credentials import ApplicationDefault
from firebase_admin.exceptions import UnavailableError
from google.api_core.exceptions import Unknown as UnknownError
from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore_v1.client import Client as CFS_Client


from test.app.cloud import fb_utils

from test.app.cloud.auth import AuthHandler
from test.app.cloud.utils import escape_email, escape_version


LOG = logging.getLogger('TEST')
LOG.setLevel(logging.DEBUG)


project_name = 'local'
# os.environ['CFS_APP_PATH'] = project_name_cfs  # set to mock project app_id
rtdb_local = os.environ.get('FIREBASE_DATABASE_EMULATOR_HOST')
rtdb_name = 'local'
rtdb_url = f'http://{rtdb_local}/'
rtdb_ns = f'?ns={rtdb_name}'
rtdb_fq = rtdb_url + rtdb_ns
_rtdb_options = {
    'databaseURL': rtdb_fq,
    'projectId': project_name
}

FIREBASE_APP = None


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


def get_firebase_app():
    global FIREBASE_APP
    if not FIREBASE_APP:
        FIREBASE_APP = firebase_admin.initialize_app(
            name=project_name,
            credential=ApplicationDefault(),
            options=_rtdb_options
        )
    return FIREBASE_APP


# @pytest.mark.integration
@pytest.fixture(scope='session')
def rtdb_options():
    yield _rtdb_options


# @pytest.mark.integration
@pytest.fixture(scope='session')
def fb_app(rtdb_options):
    yield get_firebase_app()


# @pytest.mark.integration
@pytest.fixture(scope='session')
def rtdb(fb_app):
    yield fb_utils.RTDB(fb_app)


@pytest.mark.integration
@pytest.fixture(scope='session')
def cfs():
    yield fb_utils.Firestore(
        instance=CFS_Client(
            project_name,
            credentials=AnonymousCredentials()
        ))


def get_local_session(self):
    if self.app:
        return self.app
    self.app = get_firebase_app()
    self.get_rtdb()
    self.get_cloud_firestore()
    return self.app


# raises UnavailableError
def check_app_alive(rtdb, cfs):
    ref = rtdb.reference('some/path').get()
    cref = cfs.ref(full_path=u'test2/adoc').get()
    # cref = cfs.collection(u'test2').document(u'adoc')
    return (ref and cref)


@pytest.fixture(scope='session', autouse=True)
def check_local_firebase_readyness(request, rtdb, cfs, *args):
    # @mark annotation does not work with autouse=True
    if 'unit' in request.config.invocation_params.args:
        LOG.debug('NOT Checking for LocalFirebase')
        return
    LOG.debug('Waiting for Firebase')
    for x in range(30):
        try:
            LOG.debug(check_app_alive(rtdb, cfs))
            LOG.debug(f'Firebase ready after {x} seconds')
            return
        except (UnavailableError, UnknownError, ConnectionError):
            LOG.debug(f'waiting for... {x} seconds for Firebase')
            sleep(1)

    raise TimeoutError('Could not connect to Firebase for integration test')


def get_json(path: str):
    with open(path) as f:
        return json.load(f)


@pytest.mark.integration
@pytest.fixture(scope='session')
def sample_project(rtdb, cfs, check_local_firebase_readyness):
    PATH = os.getcwd() + '/app/mock/lomis'

    META = get_json(f'{PATH}/meta/app-info.json')

    APP_ID = META['uuid']
    APP_ALIAS = META['defaultAppUuid']
    APP_VERSION = META['defaultVersion']
    APP_LANG = META['variants']

    rtdb.reference(f'/{APP_ID}/settings').set(META)
    inits = get_json(f'{PATH}/meta/inits.json')
    rtdb.reference(f'/{APP_ID}/inits').set(inits)

    rtdb.reference(
        f'apps/{APP_ALIAS}/{escape_version(APP_VERSION)}/{APP_LANG}/json') \
        .set(
            json.dumps(get_json(f'{PATH}/meta/app.json'))
    )
    schemas = get_json(f'{PATH}/meta/schemas.json')
    for i in schemas.keys():
        rtdb.reference(
            f'objects/{APP_ID}/{escape_version(APP_VERSION)}/{i}') \
            .set(
                schemas[i]
        )

    for _type in ['data', 'slots', 'tx']:
        _all = get_json(f'{PATH}/data/{_type}.json')
        _path = f'{APP_ID}'
        fb_utils.cfs_write(cfs, _all, _path)


@pytest.mark.integration
@pytest.fixture(scope='session')
def MockAuthHandler(rtdb):

    def _true(*args, **kwargs):
        return True

    with patch.object(AuthHandler, 'sign_in_with_email_and_password', _true):
        handler = AuthHandler(rtdb)
        yield handler


@pytest.mark.integration
@pytest.fixture(scope='session')
def TestSession(MockAuthHandler, rtdb):

    _user = None
    session_key = None

    def _fn(user):
        nonlocal _user
        nonlocal session_key

        _user = user
        session = MockAuthHandler.create_session(user)
        session_key = session[user]['session_key']
        return session

    yield _fn

    key = escape_email(_user)
    session_obj_ref = f'{MockAuthHandler.session_path}/{key}/{session_key}'
    rtdb.reference(session_obj_ref).delete()
