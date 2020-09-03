import json
import os

import firebase_admin
# need to import FS to use it in client
from firebase_admin import credentials, firestore  # noqa

from cloud import fb_utils, utils


def write_meta(rtdb, src, dst):
    with open(dst, 'w') as f:
        _content = rtdb.reference(src).get()
        json.dump(_content, f, indent=2, default=str)
    return _content


def write_data(cfs, src, dst):
    with open(dst, 'w') as f:
        start = cfs.document(src)
        _content = next(fb_utils.cfs_delve(start))
        json.dump(_content, f, indent=2, default=str)
    return _content


FB_DB = os.environ.get('FB_DB')
CFS_BASE_PATH = os.environ.get('LOGIAK_APP_ID')
WRITE_FOLDER = os.environ.get('WRITE_FOLDER')


cred = credentials.Certificate('service-account.json')
default_app = firebase_admin.initialize_app(cred, {
    'databaseURL': FB_DB
})

db = firebase_admin.firestore.client()
rtdb = fb_utils.RTDB(default_app)

# add your collections manually


base_types = ['data', 'tx', 'slots']

for _type in base_types:
    write_data(
        db,
        f'{CFS_BASE_PATH}/{_type}',
        f'{WRITE_FOLDER}/data/{_type}.json')

INFO = write_meta(
    rtdb,
    f'/{CFS_BASE_PATH}/settings',
    f'{WRITE_FOLDER}/meta/app-info.json')

APP_VERSION = INFO['defaultVersion']
AV_ESCAPE = utils.escape_version(APP_VERSION)
APP_ALIAS = INFO['defaultAppUuid']
APP_LANG = INFO['variants']

write_meta(
    rtdb,
    f'objects/{CFS_BASE_PATH}/{AV_ESCAPE}',
    f'{WRITE_FOLDER}/meta/schemas.json')

write_meta(
    rtdb,
    f'/{CFS_BASE_PATH}/inits',
    f'{WRITE_FOLDER}/meta/inits.json')

write_meta(
    rtdb,
    f'apps/{APP_ALIAS}/{AV_ESCAPE}/{APP_LANG}/json',
    f'{WRITE_FOLDER}/meta/app.json')
