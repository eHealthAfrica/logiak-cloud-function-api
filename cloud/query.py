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

from enum import Enum
import json
import operator
from typing import Any, get_type_hints, List, Optional, Union
from pydantic import BaseModel, validator
from pydantic.dataclasses import dataclass

from google.cloud import firestore, firestore_v1

# CFS Query API Implementation
'''
This set of classes allow the StructuredQuery Language used by the CFS REST
Interface to be accepted by the API for the purpose of filtering, ordering
and limiting data. These queries build upon a base query which is already
referenced to a particular datatype and filtered for the user based on the RBAC
rules set in logiak. As such, there is no ability to set the initial path with
CFS and the `select` directive is not accepted.
'''

import logging

LOG = logging.getLogger('QRY')
LOG.setLevel(logging.DEBUG)


# # Enums

class ValueEnum(str, Enum):

    @classmethod
    def validate(cls, v):
        try:
            return cls.lookup[v]
        except KeyError:
            raise ValueError('invalid value')

    @classmethod
    def __get_validators__(cls):
        cls.lookup = {k: v.value for k, v in cls.__members__.items()}
        yield cls.validate


class OperatorType(ValueEnum):
    LESS_THAN = '<'
    LESS_THAN_OR_EQUAL = '<='
    EQUAL = '=='
    GREATER_THAN = '>'
    GREATER_THAN_OR_EQUAL = '>='
    ARRAY_CONTAINS = 'array-contains'
    IN = 'in'
    ARRAY_CONTAINS_ANY = 'array-contains-any'


class SortDirection(ValueEnum):
    DIRECTION_UNSPECIFIED = None
    ASCENDING = firestore.Query.ASCENDING
    DESCENDING = firestore.Query.DESCENDING


# # Generic Dataclasses

@dataclass
class ObjectValue:
    booleanValue: Optional[bool] = None
    integerValue: Optional[str] = None
    doubleValue: Optional[float] = None
    timestampValue: Optional[str] = None
    stringValue: Optional[str] = None
    bytesValue: Optional[str] = None
    referenceValue: Optional[str] = None
    # Not Implemented (not used in spec)
    # # nullValue: Optional[None]
    # # geoPointValue
    # # arrayValue
    # # mapValue

    def get_value(self):
        fields = get_type_hints(self).keys()
        for f in fields:
            if (value := getattr(self, f)) is not None:
                return value


@dataclass
class FieldReference:
    fieldPath: str


# # Filters


# Unary Not Implemented in Python Library

# class UnaryOperator(ValueEnum):
#     OPERATOR_UNSPECIFIED = '0'
#     IS_NAN = '1'
#     IS_NULL = '2'

# @dataclass
# class UnaryFilterBody:
#     op: UnaryOperator
#     field: FieldReference


# @dataclass
# class UnaryFilter:
#     unaryFilter: UnaryFilterBody

#     def build(self, base: firestore_v1.query.Query):
#         return base

@dataclass
class FieldFilterBody:
    op: OperatorType
    field: FieldReference
    value: ObjectValue

    def format(self):
        return [
            self.field.fieldPath,
            self.op,
            self.value.get_value()
        ]


@dataclass
class FieldFilter:
    fieldFilter: FieldFilterBody

    def build(self, base: firestore_v1.query.Query):
        return base.where(*self.fieldFilter.format())


class CompositeFilterBody(BaseModel):
    filters: List['Filter']


@dataclass
class CompositeFilter:
    compositeFilter: CompositeFilterBody

    def build(self, base: firestore_v1.query.Query):
        for filter_ in self.compositeFilter.filters:
            base = filter_.build(base)
        return base


@dataclass
class Filter:
    filter: Union[CompositeFilter, FieldFilter]

    def build(self, base: firestore_v1.query.Query):
        return self.filter.build(base)


CompositeFilterBody.update_forward_refs()


# # OrderBy

@dataclass
class Order:
    field: FieldReference
    direction: SortDirection

    def sort(self, items: List):
        reverse = True if self.direction == 'DESCENDING' else False
        items.sort(key=operator.itemgetter(self.field.fieldPath), reverse=reverse)
        return items


# # StartAt / EndAt

@dataclass
class Cursor:
    values: List[ObjectValue]
    # default: (use start_at & end_at)
    # if true: (use start_after & end_before)
    before: bool = False

    def __make_match_filter(self, orderBy: List[Order]):
        values = [ov.get_value() for ov in self.values]
        db = [(o.field.fieldPath, values[x])
              for x, o in enumerate(orderBy) if (x < len(values))]
        LOG.debug(f'cutoff: {db}')
        getters = [operator.itemgetter(o.field.fieldPath)
                   for x, o in enumerate(orderBy) if (x < len(values))]

        def match_filter(i) -> bool:
            res = all([fn(i) == values[x] for x, fn in enumerate(getters)])
            return res

        return match_filter

    def cutoff(self, filter_, items, ascending=True) -> int:
        for x, i in enumerate(items):
            if filter_(i):
                return x

    def prune(self, orderBy: List[Order], items) -> List[Any]:
        _filter = self.__make_match_filter(orderBy)
        ascending = True if self.position == 'start' else False
        offset = 0 if not self.before else 1
        if not ascending:
            offset = offset * -1
        limit = self.cutoff(_filter, items, ascending)
        if not isinstance(limit, int) and ascending:
            # no matching startAt value, no start -> None
            return []
        if not limit and not ascending:
            # no matching endAt value, no end -> All
            return items
        # valid idx can't be < 1 in this case
        idx = max([
            0,
            limit + offset
        ])
        LOG.debug(f'{orderBy} -> {self} : @ {limit} + {offset} -> [{idx}], {ascending}')
        if ascending:
            return items[idx:]
        else:
            return items[:idx + 1]  # +1 for slice convention


@dataclass
class StartCursor(Cursor):
    position: str = 'start'


@dataclass
class EndCursor(Cursor):
    position: str = 'end'


class StructuredQuery(BaseModel):
    where: Optional[Filter] = None
    orderBy: Optional[List[Order]] = None
    startAt: Optional[StartCursor] = None
    endAt: Optional[EndCursor] = None
    limit: int = None
    offset: int = None

    @validator('startAt')
    def is_ordered_sa(cls, v, values):
        assert('orderBy' in values and values['orderBy'] is not None), \
            'startAt depends on orderBy'
        return v

    @validator('endAt')
    def is_ordered_ea(cls, v, values):
        assert('orderBy' in values and values['orderBy'] is not None), \
            'endAt depends on orderBy'
        return v

    @validator('limit')
    def nonop_limit(cls, v):
        assert False, 'limit is not Implemented'

    @validator('offset')
    def nonop_offset(cls, v):
        assert False, 'offset is not Implemented, use startAt / endAt'

    def filter(self, base: firestore_v1.query.Query):
        if self.where:
            return self.where.build(base)
        return base

    def is_ordered(self):
        return self.orderBy is not None

    def order(self, items: List):
        if self.orderBy:
            for term in reversed(self.orderBy):
                items = term.sort(items)
        if self.startAt:
            LOG.debug('-> startAt')
            items = self.startAt.prune(self.orderBy, items)
        if self.endAt:
            LOG.debug('-> endAt')
            items = self.endAt.prune(self.orderBy, items)
        return items
