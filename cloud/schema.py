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

from enum import Enum, auto
import operator
from typing import Dict

from cachetools import cached, LRUCache


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


ALLOWED_INTERNALS = [
    'created',
    'latitude',
    'longitude',
    'modified',
    'uuid',
    'version_created',
    'version_modified'
]

BANNED_INTERNALS = list(set(LOGIAK_INTERNAL_FIELDS) - set(ALLOWED_INTERNALS))


class SchemaType(Enum):
    READ = auto()
    WRITE = auto()
    ALL = auto()


_SCHEMA_REMOVE = {
    SchemaType.READ: BANNED_INTERNALS,
    SchemaType.WRITE: LOGIAK_INTERNAL_FIELDS,
    SchemaType.ALL: []
}


def strip_banned_from_msg(msg: Dict, type: SchemaType):
    filter_ = msg_stripper(type)
    return filter_(msg)


def strip_banned_from_schema(schema: Dict, type: SchemaType):
    filter_ = schema_stripper(type)
    schema['fields'] = filter_(schema.get('fields', {}))
    return schema


@cached(LRUCache(maxsize=3))
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
        return [i for i in schema if not allow(i)]

    return _stripper
