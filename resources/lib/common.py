# -*- coding: utf-8 -*-
from __future__ import unicode_literals

'''Common Kodi-related constants and functions.'''

import json
import os
import random
import urllib

import xbmc as kodi
import xbmcgui as kodigui
import xbmcplugin as kodiplugin

import utils


AUDIOFILE_SORT_METHODS = (
    kodiplugin.SORT_METHOD_FILE,
    kodiplugin.SORT_METHOD_FULLPATH,
    kodiplugin.SORT_METHOD_NONE,
    kodiplugin.SORT_METHOD_TITLE,
    kodiplugin.SORT_METHOD_TITLE_IGNORE_THE,
    kodiplugin.SORT_METHOD_TRACKNUM,
    kodiplugin.SORT_METHOD_UNSORTED,
)
AUDIOBOOK_SORT_METHODS = (
    kodiplugin.SORT_METHOD_DATEADDED,
    kodiplugin.SORT_METHOD_LASTPLAYED,
    kodiplugin.SORT_METHOD_NONE,
    kodiplugin.SORT_METHOD_TITLE,
    kodiplugin.SORT_METHOD_TITLE_IGNORE_THE,
    kodiplugin.SORT_METHOD_UNSORTED,
)
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def json_rpc(method, raise_error=False, **params):
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


def get_audio_player_id():
    resp = json_rpc('Player.GetActivePlayers')
    for player in resp.get('result', []):
        if player.get('type') == 'audio':
            return player['playerid']


def get_db_path(db_name):
    kodi_db_dir = kodi.translatePath('special://database').decode('utf-8')
    return os.path.join(kodi_db_dir, db_name)


def italic(s):
    return '[I]{0:}[/I]'.format(s)


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


def prepare_audiofile_listitem(audiobook_dir, audiobook, item, data=None):
    data = {} if data is None else data
    d = {
        'item': item.id,
    }
    d.update(data)
    cover, fanart = None, None
    if audiobook.cover:
        cover = os.path.join(audiobook_dir, audiobook.cover_path)
    if audiobook.fanart:
        fanart = os.path.join(audiobook_dir, audiobook.fanart_path)
    li = kodigui.ListItem(item.title)
    li.setInfo('music', {
        'tracknumber': item.sequence,
        'duration': item.duration,
        'album': audiobook.title,
        'artist': audiobook.author,
        'title': item.title,
        'genre': 'Audiobook',
        'size': item.size,
        'count': item.sequence,
    })
    li.setArt({
        'thumb': cover,
        'icon': cover,
        'fanart': fanart,
    })
    return li
