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
from typing import List, Optional
from pydantic.dataclasses import dataclass

# CFS Query API Implementation


class OperatorType(str, Enum):
    LESS_THAN = '<'
    LESS_THAN_OR_EQUAL = '<='
    EQUAL = '=='
    GREATER_THAN = '>'
    GREATER_THAN_OR_EQUAL = '>='
    ARRAY_CONTAINS = 'array-contains'
    IN = 'in'
    ARRAY_CONTAINS_ANY = 'array-contains-any'


# class FilterType(str, Enum):
#     compositeFilter = 'compositeFilter'
#     fieldFilter = 'fieldFilter'
#     unaryFilter = 'unaryFilter'


@dataclass
class Coercible:
    pass


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


@dataclass
class FieldReference:
    fieldPath: str


@dataclass
class FieldFilter:
    op: OperatorType
    field: FieldReference
    value: ObjectValue


@dataclass
class UnaryFilter:
    op: OperatorType
    field: FieldReference


@dataclass
class CompositeFilter:
    filters: List['Filter']


@dataclass
class Filter:
    fieldFilter: Optional[FieldFilter] = None
    unaryFilter: Optional[UnaryFilter] = None
    compositeFilter: Optional[CompositeFilter] = None

# CompositeFilter.update_forward_refs()


@dataclass
class Query:
    filter: Filter
