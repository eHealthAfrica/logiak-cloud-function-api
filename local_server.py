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

import logging

from flask import Flask, request
from . import main

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)


@app.route('/<path:text>', methods=['GET', 'POST'])
def all(text):
    if text.startswith('auth'):
        return main._auth(request)
    if text.startswith('meta'):
        return main._meta(request)
    if text.startswith('data'):
        return main._data(request)


# Add function loggers to the main Flask Logger
loggers = [
    logging.getLogger(name)
    for name in logging.root.manager.loggerDict
    if name in ['EP', 'DATA', 'QRY', 'META']
]
for l_ in loggers:
    l_.handlers.append(app.logger.handlers[0])
