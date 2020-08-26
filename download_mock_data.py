import json
import os

import firebase_admin
# need to import FS to use it in client
from firebase_admin import credentials, firestore  # noqa

FB_DB = os.environ.get('FB_DB')
CFS_BASE_PATH = os.environ.get('CFS_APP_PATH')
WRITE_FOLDER = os.environ.get('WRITE_FOLDER')


cred = credentials.Certificate('service-account.json')
default_app = firebase_admin.initialize_app(cred, {
    'databaseURL': FB_DB
})

db = firebase_admin.firestore.client()

# add your collections manually

collections = dict()
dict4json = dict()
n_documents = 0

base_types = ['data', 'tx', 'slots']

for _type in base_types:
    with open(f'{WRITE_FOLDER}/{_type}.json', 'w') as f:
        docs = {}
        collections = db.document(f'{CFS_BASE_PATH}/{_type}').collections()
        for collection in collections:
            docs[collection.id] = [d.to_dict() for d in collection.get()]
        json.dump(docs, f, indent=2, default=str)
