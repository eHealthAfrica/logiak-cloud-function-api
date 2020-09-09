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
import json

from flask import jsonify, make_response, Response
from spavro.schema import parse

from . import fb_utils, meta, utils
from .auth import AuthHandler, auth_request, require_auth

ROOT_PATH = os.environ.get('ROOT_PATH')
_STRIP = utils.path_stripper([ROOT_PATH])


SCHEMAS = {}

APP = None
CFS = fb_utils.Firestore(APP)
RTDB = fb_utils.RTDB(APP)
AUTH_HANDLER = AuthHandler(RTDB)


# actual request handlers


# route all from base path (usually APP_ID, name or alias)
def route_all(request):
    root = _STRIP(request.path.split('/'))[0]
    if root == 'auth':
        return handle_auth(request)
    elif root == 'meta':
        return handle_meta(request)
    # elif root == 'data':
    #     return handle_data(request)
    return Response('Not Found', 404)


def handle_auth(request):
    data = request.get_json(force=True, silent=True)
    return auth_request(data, AUTH_HANDLER)


@require_auth(AUTH_HANDLER)
def handle_no_op(request):
    return Response('', 200)


@require_auth(AUTH_HANDLER)
def handle_meta(request):
    path = request.path.split('/')
    return meta.resolve(path, RTDB)


# def __data_all(name):
#     if name not in DATA:
#         raise KeyError
#     yield "["
#     for i in DATA[name]:
#         yield json.dumps(i) + ','
#     yield "]"


# @require_auth(AUTH_HANDLER)
# def handle_data(request):
#     path = request.path.split('/')
#     try:
#         local_path = (path.index('data') + 1)
#     except ValueError:
#         local_path = 1
#     path = path[local_path:]
#     try:
#         if path[1] == 'query':
#             name = path[0]
#             if name in DATA:  # keyError from Generator was causing problems
#                 return Response(
#                     __data_all(path[0]),
#                     200,
#                     mimetype='application/json')
#     except Exception:
#         pass
#     return Response(f'Not Found @ {path}', 404)
