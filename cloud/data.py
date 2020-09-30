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

# import json

# from flask import jsonify, make_response, Response

from spavro.schema import parse

import json
import logging
import os
from typing import Iterator, List, Generator

from flask import Response
from pydantic.error_wrappers import ValidationError as PydanticValidationError

from . import fb_utils
from .query import StructuredQuery
from .utils import chunk, escape_email, path_stripper

from google.cloud import firestore_v1


LOG = logging.getLogger('DATA')
LOG.setLevel(logging.DEBUG)


APP_ID = os.environ.get('LOGIAK_APP_ID')
APP_ALIAS = None

# root path for testing (usually APP_ID)
ROOT_PATH = os.environ.get('ROOT_PATH')

_STRIP = path_stripper([ROOT_PATH, 'data']) \
    if ROOT_PATH \
    else path_stripper(['data', ''])


def resolve(user_id, path: List, cfs: fb_utils.Firestore, data=None) -> Response:
    path = _STRIP(path)
    try:
        _type = path[0]
        if path[1] == 'read':
            _id = path[2]
            if doc := _get(cfs, user_id, _type, _id):
                return Response(doc, 200, mimetype='application/json')
        elif path[1] == 'query':
            try:
                if data:
                    # validate outside of the generator
                    data = StructuredQuery(**data)
                _response_generator = _query(cfs, user_id, _type, data)
                return Response(_response_generator, 200, mimetype='application/json')
            except PydanticValidationError as pvr:
                return Response(f'Invalid StructuredQuery: {pvr}', 400, mimetype='application/text')
        elif path[1] == 'create':
            return Response('Not implemented', 501)
    except IndexError:
        pass
    return Response(f'Not Found @ {path}', 404)

# read


def _is_eligible(cfs: fb_utils.Firestore, user_id: str, _type: str, _id) -> bool:
    escaped_id = escape_email(user_id)
    uri = f'{APP_ID}/slots/{escaped_id}/data/{_type}/{_id}'
    return cfs.ref(full_path=uri).get().exists


def _eligible_docs(cfs: fb_utils.Firestore, user_id: str, _type: str):
    escaped_id = escape_email(user_id)
    uri = f'{APP_ID}/slots/{escaped_id}/data/{_type}'
    return cfs.list(path=uri)


def _get(
    cfs: fb_utils.Firestore,
    user_id: str,
    _type: str,
    _id: str
):
    if not _is_eligible(cfs, user_id, _type, _id):
        return
    uri = f'{APP_ID}/data/{_type}/{_id}'
    _doc = cfs.ref(full_path=uri).get()
    if _doc:
        return json.dumps(_doc.to_dict(), sort_keys=True)


def _query(
    cfs: fb_utils.Firestore,
    user_id: str,
    _type: str,
    structured_query: StructuredQuery = None
) -> Generator:
    # raises validation errors
    _ids = chunk(_eligible_docs(cfs, user_id, _type), 10)
    uri = f'{APP_ID}/data/{_type}'
    ref = cfs.ref(path=uri)
    # if the query is not ordered then we can stream it directly
    if not structured_query or not structured_query.is_ordered():
        yield from unordered_query(ref, structured_query, _ids)
    else:
        yield from ordered_query(ref, structured_query, _ids)


def unordered_query(
    query_: firestore_v1.query.Query,
    structured_query: StructuredQuery,
    _ids: Iterator[str]
):
    # in case of a whole lot of records, we can build a generator to stream them directly.
    # This should be the fastest way to do so, but only worked for unordered queries
    # because of the way that we implement Logiak's  RBAC, by pulling all the valid IDs,
    # and the CFS limitation that an "in" query can only have 10 values.
    # Yielding chunks of json is however quite tricky to implement as the number is unknown
    # 0 >= n_docs <= Infinity?

    yield '['
    # we have to hold off on adding the last element to make the json format properly
    last = None
    # we also have to keep track of whether we only have on record total so we don't break
    # formatting when we add the last one at the end.
    only = True
    for _from in _ids:
        query_ = query_.where(u'uuid', u'in', _from)
        if structured_query:
            query_ = structured_query.filter(query_)
        res = list(query_.stream())
        if not res:
            continue
        elif res and last:
            only = False
            yield ','
            yield json.dumps(last.to_dict(), sort_keys=True)
            yield ','
        elif res and not last:
            last = res[-1]
            res = res[:-1]
            if res:
                only = False
                yield ','.join(
                    [json.dumps(doc.to_dict(), sort_keys=True) for doc in res[:len(res)]]
                )
    if last:
        if not only:
            yield ','
        yield json.dumps(last.to_dict(), sort_keys=True)
    yield ']'


def all_matching_docs(
    query_: firestore_v1.query.Query,
    structured_query: StructuredQuery,
    _ids: Iterator[str]
):
    for _from in _ids:
        query_ = query_.where(u'uuid', u'in', _from)
        if structured_query:
            query_ = structured_query.filter(query_).stream()
        for doc in query_:
            yield doc.to_dict()


def ordered_query(
    query_: firestore_v1.query.Query,
    structured_query: StructuredQuery,
    _ids: Iterator[str]
):
    docs = list(all_matching_docs(query_, structured_query, _ids))
    docs = structured_query.order(docs)
    yield json.dumps(docs, sort_keys=True)


# write

def logiak_requires(user_name, doc):
    '''
    apk_version_created
    "0.0.127+92"
    apk_version_modified
    "0.0.127+92"
    created
    "1599651061113"
    data_collector_email
    "mustapha.barda@ehealthnigeria.org"
    email
    "mustapha.barda@ehealthnigeria.org"
    firebase_uuid
    "1eJBkcPZDUQrjvBJ9FxOQ6M1c0r1"
    group_uuid
    "449351b4-bd5c-4358-bba8-8b8d410819c2"
    latitude
    "12.0199774"
    longitude
    "8.5637202"
    managed_uuid
    "cfc3278c-f808-4bcf-9f66-d91235ac3e2b"
    modified
    "1599651061112"
    program
    ""
    quantity
    "1.0"
    role_uuid
    "d6b81831-4bb2-4712-bcaa-e522c456a270"
    slot
    # null
    uuid
    # "14337a2a-f5b9-4ed7-943b-e4ccccfaf907"
    version_created
    # "0.0.42"
    version_modified
    # "0.0.42"
    '''
    pass
