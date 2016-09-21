# -*- coding: utf-8 -*-
from __future__ import unicode_literals

'''Common Kodi-related constants and functions.'''

import os
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


def get_db_path(db_name):
    kodi_db_dir = kodi.translatePath('special://database')
    return os.path.join(kodi_db_dir, db_name)


def italic(s):
    return '[I]{0:}[/I]'.format(s)


def parse_comment(comment):
    if comment.startswith('ausis:'):
        return utils.load_data(comment[len('ausis:'):])
    return {}


def dump_comment(data):
    return 'ausis:{0:s}'.format(utils.dump_data(data))


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


def prepare_audiofile_listitem(audiobook_dir, audiobook, item, data=None):
    data = {} if data is None else data
    d = {
        'item': item[b'id'],
    }
    d.update(data)
    audiobook_path = audiobook[b'path']
    cover = audiobook[b'cover_path']
    if cover:
        cover = os.path.join(audiobook_dir, audiobook_path, cover)
    fanart = audiobook[b'fanart_path']
    if fanart:
        fanart = os.path.join(audiobook_dir, audiobook_path, fanart)
    li = kodigui.ListItem(item[b'title'])
    li.setInfo('music', {
        'tracknumber': item[b'sequence'],
        'duration': int(item[b'duration']),
        'album': audiobook[b'title'],
        'artist': audiobook[b'author'],
        'title': item[b'title'],
        'genre': 'Audiobook',
        'comment': dump_comment(d),
        'size': item[b'size'],
        'count': item[b'sequence'],
    })
    li.setArt({
        'thumb': cover,
        'icon': cover,
        'fanart': fanart,
    })
    return li
