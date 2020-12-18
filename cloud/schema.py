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

from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum, auto
import json
import logging
import operator
from typing import Callable, Dict, List

from cachetools import cached, LRUCache
from cachetools.keys import hashkey
from spavro.schema import SchemaParseException

from . import fb_utils


LOG = logging.getLogger('SCHEMA')
LOG.setLevel(logging.DEBUG)

AVRO_TYPES = {  # from string
    'boolean': bool,
    'int': int,
    'long': int,
    'float': float,
    'double': float,
    'bytes': lambda x: b'x',
    'string': str,
    'record': lambda x: json.loads(x),
    'enum': str,
    'array': lambda x: json.loads(x),
    'fixed': str,
    'object': lambda x: json.loads(x),
    'array:string': lambda x: json.loads(x)
}

LOGIAK_INTERNAL_FIELDS = [
    'apk_version_created',
    'apk_version_modified',
    'created',
    'email',
    'firebase_uuid',
    'group_uuid',
    'latitude',
    'longitude',
    'managed_uuid',
    'modified',
    'role_uuid',
    'slot',
    'uuid',
    'version_created',
    'version_modified'
]

LOGIAK_INTERNAL_REQUIRED_WRITE = [
    'uuid'
]

BANNED_WRITE = list(set(LOGIAK_INTERNAL_FIELDS) - set(LOGIAK_INTERNAL_REQUIRED_WRITE))


ALLOWED_INTERNALS = [
    'created',
    'latitude',
    'longitude',
    'modified',
    'uuid',
    'version_created',
    'version_modified'
]

BANNED_READ = list(set(LOGIAK_INTERNAL_FIELDS) - set(ALLOWED_INTERNALS))


# ignores arg[0] for the purpose of cache keying (in this case rtdb: fb_utils:RTDB)
def key_ignore_db(*args, **kwargs):
    return hashkey(*args[1:], **kwargs)


class SchemaType(Enum):
    READ = auto()
    WRITE = auto()
    ALL = auto()


_SCHEMA_REMOVE = {
    SchemaType.READ: BANNED_READ,
    SchemaType.WRITE: BANNED_WRITE,
    SchemaType.ALL: []
}


def strip_banned_from_msg(rtdb: fb_utils.RTDB, msg: Dict, schema_name: str, type: SchemaType):
    cast_ = schema_caster(rtdb, schema_name, msg.get('version_modified'))
    filter_ = msg_stripper(type)
    return cast_(filter_(msg))


def strip_banned_from_schema(schema: Dict, type: SchemaType):
    filter_ = schema_stripper(type)
    schema['fields'] = filter_(schema.get('fields', {}))
    return schema


# not recursive so doesn't work on nested schemas, but neither does logiak
@cached(LRUCache(maxsize=100), key=key_ignore_db)
def schema_caster(rtdb: fb_utils.RTDB, schema_name: str, version: str) -> Callable[[Dict], Dict]:
    # have to import here to avoid circular reference in meta
    from .meta import _meta_schema, _meta_info
    if not (schema := _meta_schema(rtdb, version, schema_name, SchemaType.ALL)):
        default_version = _meta_info(rtdb).get('defaultVersion')
        if not (schema := _meta_schema(rtdb, default_version, schema_name, SchemaType.ALL)):
            raise RuntimeError(
                f'No schema found for {schema_name} on {version} or default: {default_version}')
    trans = {}
    # if we don't deepcopy, we'll mutate the cached schema to always be strict
    schema = deepcopy(schema)
    fields = [field_remove_optional(f) for f in schema['fields']]
    for field in fields:
        type_ = field['type'] if len(field['type']) > 1 else field['type'][-1]
        trans[field['name']] = AVRO_TYPES.get(type_, 'string')

    def cast(msg: Dict) -> Dict:
        nonlocal trans
        res = {}
        for k, v in msg.items():
            try:
                res[k] = trans[k](v)
            except Exception:
                pass
        return res

    return cast


# internally, everything in CFS for logiak is a string and cannot be null, must be ''
def cast_values_to_string(msg: Dict):
    return {k: str(v) if v is not None else '' for k, v in msg.items()}


@cached(LRUCache(maxsize=3), key=key_ignore_db)
def msg_stripper(_type: SchemaType):
    list_ = _SCHEMA_REMOVE[_type]

    def filter_(msg):
        return {k: msg[k] for k in msg.keys() if k not in list_}

    return filter_


def schema_filter(_type: SchemaType):

    _name = operator.itemgetter('name')
    list_ = _SCHEMA_REMOVE[_type]

    def _is_allowed(field) -> bool:
        if _name(field) in list_:
            return False
        return True
    return _is_allowed


@cached(LRUCache(maxsize=3))
def schema_stripper(_type: SchemaType):
    allow = schema_filter(_type)

    def _stripper(schema):
        return [i for i in schema if allow(i)]

    return _stripper


@cached(LRUCache(maxsize=128), key=key_ignore_db)
def schema_flag_extras(rtdb: fb_utils.RTDB, schema_name, schema_version) -> Callable:
    from .meta import _meta_schema
    schema = _meta_schema(rtdb, schema_version, schema_name, SchemaType.ALL)
    allowed = [f.get('name') for f in schema['fields']]

    def validate(msg) -> List:
        if len(msg) < 2:  # only uuid present
            return ['Empty document']
        if any(extra_fields := [k for k in msg.keys() if k not in allowed]):
            return [f'extra field: {k}' for k in extra_fields]
        return []
    return validate


def strict_schema(schema: Dict):
    '''
    If a new document is to be created, it __must__ have the logiak fields filled
    even if their value is "" so we make a strict schema in which null is not in the union.
    '''
    schema['fields'] = [
        field_remove_optional(f)
        if f['name'] in LOGIAK_INTERNAL_FIELDS
        else f
        for f in schema['fields']
    ]
    return schema


def field_remove_optional(field: Dict):
    if not isinstance(field.get('type'), list):
        return field
    field['type'].remove('null')
    field['type'] = field['type'] if len(field['type']) > 1 else field['type'][-1]
    return field


def compliant_create_doc(rtdb: fb_utils.RTDB, update_doc: Dict, user_id: str):
    # add fields to compliant update doc, to make compliant create doc
    # but don't mutate it because update_doc is the failback if doc exists in CFS
    # avoid circular imports
    from .meta import meta_user_init_info
    user_info = meta_user_init_info(rtdb, user_id)
    doc = update_doc.copy()
    doc['apk_version_created'] = doc['apk_version_modified']
    doc['created'] = doc['modified']
    doc['data_collector_email'] = user_id
    doc['email'] = user_id
    # user's role uuid
    doc['role_uuid'] = user_info.get('roleUuid') or ''
    # user's firebase auth uuid
    doc['firebase_uuid'] = user_info.get('firebaseUuid') or ''
    # user's groupUuid
    doc['group_uuid'] = user_info.get('groupUuid') or ''
    # user's managedUuid
    doc['managed_uuid'] = user_info.get('managedUuid') or ''
    doc['version_created'] = doc['version_modified']
    return doc


def compliant_update_doc(doc: Dict, version: str):
    # add internal fields to create compliant update doc
    doc['apk_version_modified'] = doc.get('apk_version_modified') or ''
    doc['modified'] = int(round(datetime.now(timezone.utc).timestamp() * 1000))
    doc['version_modified'] = version
    doc['latitude'] = doc.get('latitude')
    doc['longitude'] = doc.get('longitude')
    return doc
