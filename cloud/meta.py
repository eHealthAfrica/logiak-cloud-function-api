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

import json
import logging
import os
from typing import List

from cachetools import cached, LRUCache, TTLCache
from cachetools.keys import hashkey
from flask import Response
import spavro.schema


from . import fb_utils
from .schema import strip_banned_from_schema, SchemaType
from .utils import escape_email, escape_version, path_stripper


LOG = logging.getLogger('META')
LOG.setLevel(logging.DEBUG)


APP_ID = os.environ.get('LOGIAK_APP_ID')
APP_ALIAS = None

# root path for testing (usually APP_ID)
ROOT_PATH = os.environ.get('ROOT_PATH')

_STRIP = path_stripper([ROOT_PATH, 'meta']) \
    if ROOT_PATH \
    else path_stripper(['meta', ''])


# ignores arg[0] for the purpose of cache keying (in this case rtdb: fb_utils:RTDB)
def key_ignore_db(*args, **kwargs):
    return hashkey(*args[1:], **kwargs)


def as_json_response(obj) -> Response:
    if obj is not None:
        return Response(json.dumps(obj), 200, mimetype='application/json')
    return Response('Not Found', 404)


def resolve(path, rtdb: fb_utils.RTDB) -> Response:
    path = _STRIP(path)
    try:
        if path[0] == 'schema':
            if len(path) == 2:
                return as_json_response(_meta_list_schemas(rtdb, path[1]))
            if len(path) == 3:
                return as_json_response(_meta_schema(rtdb, path[1], path[2]))
        elif path[0] == 'app':
            if len(path) < 2:
                return as_json_response(_meta_info(rtdb))
            else:
                return as_json_response(_meta_app(rtdb, path[1], path[2]))
    except IndexError:
        # could not parse args
        pass
    return Response(f'Not Found @ {path}', 404)


# /meta/app [GET]
# -> {app_id}/settings
@cached(cache=TTLCache(maxsize=1, ttl=300), key=key_ignore_db)
def _meta_info(rtdb: fb_utils.RTDB) -> dict:
    uri = f'{APP_ID}/settings'
    return rtdb.reference(uri).get()


# /meta/app/{app_version}/{app_language} [GET]
# -> apps/{app_alias}/{app_version(escaped)}/{language}/json
@cached(LRUCache(maxsize=32), key=key_ignore_db)
def _meta_app(rtdb: fb_utils.RTDB, app_version: str, app_language: str) -> dict:
    global APP_ALIAS
    if not APP_ALIAS:
        APP_ALIAS = _meta_info(rtdb)['defaultAppUuid']
    _version = escape_version(app_version)
    uri = f'apps/{APP_ALIAS}/{_version}/{app_language}/json'
    res = rtdb.reference(uri).get()
    if res:
        return json.loads(res)


# /meta/schema/{app_version} [GET]
# -> objects/{app_id}/{app_version(escaped)}
@cached(LRUCache(maxsize=32), key=key_ignore_db)
def _meta_list_schemas(rtdb: fb_utils.RTDB, app_version: str) -> List:
    _version = escape_version(app_version)
    uri = f'objects/{APP_ID}/{_version}'
    res = rtdb.reference(uri).get(shallow=True)
    if res:
        return sorted(res.keys())


# /meta/schema/{app_version}/{schema_name}` [GET]
# -> objects/{app_id}/{app_version(escaped)}/{schema_name}
@cached(LRUCache(maxsize=32), key=key_ignore_db)
def _meta_schema(
    rtdb: fb_utils.RTDB,
    app_version: str,
    schema_name: str,
    type: SchemaType = SchemaType.READ
) -> dict:
    _version = escape_version(app_version)
    uri = f'objects/{APP_ID}/{_version}/{schema_name}'
    res = rtdb.reference(uri).get()
    if res:
        _schema = json.loads(res)
        return strip_banned_from_schema(_schema, type)


@cached(LRUCache(maxsize=32), key=key_ignore_db)
def meta_schema_object(
    rtdb: fb_utils.RTDB,
    app_version: str,
    schema_name: str,
    type: SchemaType = SchemaType.READ
) -> spavro.schema.Schema:
    meta_ = json.dumps(
        _meta_schema(
            rtdb, app_version, schema_name, type
        ))
    if meta_:
        return spavro.schema.parse(meta_)


@cached(LRUCache(maxsize=128), key=key_ignore_db)
def meta_user_init_info(
    rtdb: fb_utils.RTDB,
    email: str
):
    key = escape_email(email)
    uri = f'{APP_ID}/inits/{key}'
    if not (doc := rtdb.reference(uri).get()):
        return {}
    return doc
