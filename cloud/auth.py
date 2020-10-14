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

from functools import wraps
import json
import logging
import os
from time import time as epoch_now
from typing import Dict
from uuid import uuid4

from cachetools import cached, TTLCache
from cachetools.keys import hashkey
from flask import Response
import requests

from .fb_utils import RTDB
from .utils import escape_email, missing_required


LOG = logging.getLogger('AUTH')
LOG.setLevel(logging.DEBUG)


def require_auth(auth: 'AuthHandler'):
    def handler(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            headers = dict(request.headers)
            reqs = ['Logiak-User-Id', 'Logiak-Session-Key']
            if (missing := missing_required(headers, reqs)):  # noqa
                return Response(f'Missing required headers: {missing}', 400)
            user_id, user_token = headers[reqs[0]], headers[reqs[1]]
            if not auth.verify_session(user_id, user_token):
                return Response('Bad Session', 401)
            return fn(request, *args, **kwargs)
        return wrapper
    return handler


def ignore_self(*args, **kwargs):
    return hashkey(*args[1:], **kwargs)


class AuthHandler(object):

    ID_URL = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword'
    # https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword

    def __init__(self, rtdb: RTDB):
        self.api_key = os.environ.get('WEB_API_KEY')
        self.app_id = os.environ.get('LOGIAK_APP_ID')
        self.session_length = os.environ.get('SESSION_LENGTH', 60 * 60 * 24)
        self.rtdb = rtdb
        self.session_path = f'/webapp/{self.app_id}/session'

    def sign_in_with_email_and_password(self, email: str, password: str) -> bool:
        url = f'{self.ID_URL}?key={self.api_key}'
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps({'email': email, 'password': password, 'returnSecureToken': False})
        res = requests.post(url, headers=headers, data=data)
        try:
            res.raise_for_status()
        except Exception as err:
            LOG.debug(f'signing error: {err}')
            return False
        return True

    def create_session(self, user_id: str) -> Dict:
        key = escape_email(user_id)
        self._remove_expired_sessions(key)
        user_token_path = f'{self.session_path}/{key}'
        session = self._generate_session()
        ref = self.rtdb.reference(f'{user_token_path}/{session["session_key"]}')
        ref.set(session)
        return {user_id: session}

    def user_has_app_access(self, email: str) -> bool:
        key = escape_email(email)
        uri = f'{self.app_id}/inits/{key}/version'
        ref = self.rtdb.reference(uri)
        if ref.get():
            return True
        return False

    def _session_is_valid(self, session) -> bool:
        try:
            now = epoch_now()
            expiry = session['session_length'] + session['start_time']
            return now <= expiry
        except Exception as err:
            LOG.debug(f'session validation error: {err}')
            return False

    def _remove_expired_sessions(self, user_id):
        key = escape_email(user_id)
        all_session_path = f'{self.session_path}/{key}'
        sessions = self.rtdb.reference(all_session_path).get()
        if not sessions:
            return
        for _id, session in sessions.items():
            if not self._session_is_valid(session):
                self.rtdb.reference(f'{all_session_path}/{_id}').delete()

    def _generate_session(self) -> Dict:
        return {
            'session_key': str(uuid4()),
            'start_time': epoch_now(),
            'session_length': self.session_length
        }

    @cached(cache=TTLCache(maxsize=32, ttl=60), key=ignore_self)
    def verify_session(self, user_id: str, token: str) -> bool:
        key = escape_email(user_id)
        user_token_path = f'{self.session_path}/{key}/{token}'
        session = self.rtdb.reference(user_token_path).get()
        if session:
            return self._session_is_valid(session)
        return False


def auth_request(data, auth_handler):
    required = ['username', 'password']
    if (missing := missing_required(data, required)):
        return Response(f'Missing expected data: {missing}', 400)
    if not auth_handler.sign_in_with_email_and_password(data['username'], data['password']):
        return Response('Bad Credentials', 401)
    if not auth_handler.user_has_app_access(data['username']):
        return Response('Invalid user for application', 401)
    session = auth_handler.create_session(data['username'])
    return Response(
        json.dumps(session),
        200,
        mimetype='application/json')
