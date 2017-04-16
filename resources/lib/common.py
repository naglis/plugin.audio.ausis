# -*- coding: utf-8 -*-
from __future__ import unicode_literals

'''Common Kodi-related constants and functions.'''

import json
import os
import random
import urllib

import xbmc as kodi

import utils


DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def json_rpc(method, **params):
    values = {
        'jsonrpc': '2.0',
        'method': method,
        'id': random.randint(1, 10000000),
    }
    if params:
        values.update({
            'params': params,
        })
    return json.loads(kodi.executeJSONRPC(json.dumps(values)))


def get_db_path(db_name):
    kodi_db_dir = kodi.translatePath('special://database').decode('utf-8')
    return os.path.join(kodi_db_dir, db_name)


def parse_comment(comment):
    if comment.startswith('ausis:'):
        return utils.load_data(comment[len('ausis:'):])
    return {}


def dump_comment(data):
    return 'ausis:{0:s}'.format(utils.dump_data(data))


class KodiPlugin(object):

    _strings = {}

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
        if isinstance(string_id, basestring):
            string_id = self._strings[string_id]
        return self._addon.getLocalizedString(string_id)

    def log(self, msg, level=kodi.LOGDEBUG):
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
