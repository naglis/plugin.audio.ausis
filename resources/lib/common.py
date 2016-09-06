from __future__ import unicode_literals

'''Common Kodi-related functions.'''

import os
import urllib

import xbmc as kodi

import utils


def get_db_path(db_name):
    kodi_db_dir = kodi.translatePath('special://database')
    return os.path.join(kodi_db_dir, db_name)


class KodiPlugin(object):

    def __init__(self, base_url, handle, addon):
        self._base_url = base_url
        self._handle = handle
        self._addon = addon

    def _build_url(self, **kwargs):
        '''Build and returns a plugin  URL.'''
        return '%s?%s' % (
            self._base_url, urllib.urlencode(utils.encode_values(kwargs))
        )

    def _t(self, string_id):
        '''A shorthand to addon.getLocalizedString.'''
        return self._addon.getLocalizedString(string_id)

    def log(self, msg, level=kodi.LOGDEBUG):
        log_enabled = (
            self._addon.getSetting('logging_enabled').lower() == 'true' or not
            level == kodi.LOGDEBUG)
        if log_enabled:
            msg = ('%s: %s' % (
                self._addon.getAddonInfo('id'), msg)).encode('utf-8')
            kodi.log(msg=msg, level=level)

    def run(self, args):
        mode = args.get('mode') or 'main'
        mode_handler = 'mode_%s' % mode
        if hasattr(self, mode_handler):
            return getattr(self, mode_handler)(args)
        else:
            self.log(
                'Plugin called with unknown mode: %s' % mode,
                level=kodi.LOGERROR,
            )
