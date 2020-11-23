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
from pydantic.error_wrappers import ValidationError

from test.app.cloud import utils, query, schema


@pytest.mark.unit
def test__clean_list():
    to_remove = ['a', 'b', 'c']

    _fn = utils.path_stripper(to_remove)

    for path in (
        ['a', 'b', 'c', 'd'],
        ['a', 'b', 'd'],
        ['d', 'e']
    ):
        res = _fn(path)
        assert(not any([i in res for i in to_remove]))
        assert(len(res) > 0)


@pytest.mark.parametrize('body,valid', (
    ('''{
      "where" : {
        "filter": {
          "fieldFilter": {
            "field": {"fieldPath": "name"},
            "op": "EQUAL",
            "value": {"booleanValue": "true"}
          }
        }
      }
    }''', True),
    # bad enum value
    ('''{
      "where" : {
        "filter": {
          "fieldFilter": {
            "field": {"fieldPath": "name"},
            "op": "MISSING",
            "value": {"booleanValue": "true"}
          }
        }
      }
    }''', False),
    # extra info
    ('''{
      "bad_query_header" : {}
    }''', True),
    # bad sub - fields
    ('''{
      "where" : {
        "filter": {
          "unaryFilter": {
            "field": {"fieldPath": "name"},
            "value": {"booleanValue": "true"}
          }
        }
      }
    }''', False),
    # use Unary Filter (not implemented in Python)
    ('''{
      "where" : {
        "filter": {
          "unaryFilter": {
            "field": {"fieldPath": "name"},
            "op": "IS_NAN"
          }
        }
      }
    }''', False),
    # only set order
    ('''{
      "orderBy" : [
          {
            "field": {"fieldPath": "name"},
            "direction": "ASCENDING"
          }
        ]
    }''', True),
    # empty orderBy
    ('''{
      "orderBy" : [
        ]
    }''', True),
    ('''{
      "orderBy" : [
          {
            "field": {"fieldPath": "someDate"},
            "direction": "ASCENDING"
          }
        ],
      "startAt" : {
        "values" : [
            {"booleanValue": "true"}
        ]}
    }''', True),
    # missing orderBy
    ('''{
      "startAt" : { "values": [
            {"booleanValue": "true"}
        ]}
    }''', False),
    # not allowed.
    ('''{
      "limit": 1
    }''', False),
    # not allowed.
    ('''{
      "offset": 1
    }''', False),
))
@pytest.mark.unit
def test__parse_query_json(body, valid):
    if not valid:
        with pytest.raises(ValidationError):
            _q = query.StructuredQuery.parse_raw(body)
    else:
        _q = query.StructuredQuery.parse_raw(body)
        assert(_q.dict())


@pytest.mark.unit
def test__field_remove_optional():
    a = {
        'name': 'a',
        'type': [
            'null',
            'string'
        ]
    }
    b = {
        'name': 'a',
        'type': 'string'
    }
    c = {
        'name': 'a',
        'type': [
            'null',
            'string',
            'int'
        ]
    }
    d = {
        'name': 'geometry',
        'type': [
            'null',
            {
                'name': 'geometry',
                'type': 'record',
                'fields': [
                    {
                        'name': 'latitude',
                        'type': [
                            'null',
                            'float'
                        ],
                        'namespace': 'MySurvey.geometry'
                    }
                ]
            }
        ]
    }
    assert(schema.field_remove_optional(a)['type'] == 'string')
    assert(schema.field_remove_optional(b)['type'] == 'string')
    res_c = schema.field_remove_optional(c)
    assert(isinstance(res_c['type'], list))
    assert('null' not in res_c['type'])
    assert(isinstance(schema.field_remove_optional(d)['type'], dict))
