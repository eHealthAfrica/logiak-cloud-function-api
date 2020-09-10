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

import types

from firebase_admin.db import reference as rtdb_reference
from firebase_admin.firestore import client as cfs_client
from google.cloud import firestore
from google.cloud.firestore_v1.collection import CollectionReference


# RTDB io

class RTDB(object):

    def __init__(self, app):
        self.app = app

    def reference(self, path):
        return rtdb_reference(path, app=self.app)


# CFS io

class Firestore(object):
    cfs: firestore.Client = None

    def __init__(self, app=None, instance=None):
        if app:
            self.cfs = cfs_client(app)
        elif instance:
            self.cfs = instance

    def read(self, path=None, _id=None, doc_path=None):
        if doc_path:
            return self.ref(full_path=doc_path).get()
        if _id:
            return self.ref(path, _id).get().to_dict()
        else:
            return [i.to_dict() for i in self.ref(path, _id).get()]

    def ref(self, path=None, _id=None, full_path=None):
        if full_path:
            return self.cfs.document(full_path)
        if _id:
            path = f'{path}/{_id}'
            return self.cfs.document(path)
        else:
            return self.cfs.collection(path)

    def list(self, path=None, _id=None, full_path=None):
        return [i.id for i in self.ref(path, _id, full_path).list_documents()]

    def write(self, path=None, value=None, _id=None, full_path=None):
        _set_ref = self.ref(path, _id, full_path)
        if isinstance(_set_ref, CollectionReference):
            return _set_ref.add(value, document_id=_id)
        else:
            return _set_ref.set(value)

    def remove(self, path, _id=None):
        return self.ref(path, _id).delete()


# recursive generator to extract data from a nested CFS path
# USAGE: all_docs = next(cfs_delve(head_document))
def cfs_delve(doc):  # pragma nocover  # used in scraper, not app
    if isinstance(doc, CollectionReference):
        yield from (cfs_delve(doc) for doc in doc.list_documents())
    else:
        collections = doc.collections()
        if collections:
            res = {}
            for collection in collections:
                _docs = (cfs_delve(doc) for doc in collection.list_documents())
                res[collection.id] = {}
                for d in _docs:
                    if not isinstance(d, types.GeneratorType):
                        __doc = d.get()
                        res[collection.id][d.id] = __doc.to_dict()
                    else:
                        [res[collection.id].update(i) for i in d]
            yield {doc.id: res or doc.get().to_dict()}
        else:
            yield doc


# is a document actually a terminal document?
# we write from the bottom up, creating parent documents are required
def __is_terminus(doc):
    if not isinstance(doc, dict):
        return False
    for k, v in doc.items():
        if isinstance(v, dict):
            return False
    return True


# children of missing documents don't show up in the emulator
# so we add parent documents starting from a terminal path
def __write_parents(db: Firestore, terminus_path):
    try:
        path = terminus_path
        while path := '/'.join(path.split('/')[:-2]):
            db.write(full_path=path, value={})
    except Exception:
        pass


def cfs_write(db: Firestore, doc, current_path):
    if __is_terminus(doc):
        __write_parents(db, current_path)
        db.write(full_path=current_path, value=doc)
        return
    for k, v in doc.items():
        cfs_write(db, v, f'{current_path}/{k}')
