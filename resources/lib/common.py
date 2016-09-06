from __future__ import unicode_literals

'''Common Kodi-related functions.'''

import os

import xbmc as kodi


def get_db_path(db_name):
    kodi_db_dir = kodi.translatePath('special://database')
    return os.path.join(kodi_db_dir, db_name)
