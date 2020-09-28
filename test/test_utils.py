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

import json

import pytest

from test.app.cloud import utils, query


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


@pytest.mark.unit
def test__parse_query_json():
    simple_filter = '''
    {
      "fieldFilter": {
        "field": {"fieldPath": "name"},
        "op": "EQUAL",
        "value": {"stringValue": "XYZ"}
      }
    }
    '''
    _q = query.Query(filter=json.loads(simple_filter))
    _q.validate()
