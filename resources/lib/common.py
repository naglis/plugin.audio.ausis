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

# I know, I know... This is just mild obfuscation.
SENTRY_URL = (
    '68747470733a2f2f653532396430633836653434343931336161323263376166633639336'
    '23634313a3937636438383234393265663432393838366534313730376635633035636130'
    '4073656e7472792e696f2f313031383937').decode('hex')


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
        'comment': dump_comment(d),
        'size': item.size,
        'count': item.sequence,
    })
    li.setArt({
        'thumb': cover,
        'icon': cover,
        'fanart': fanart,
    })
    return li


class LazyRavenClient(object):
    '''
    Lazy Raven client context manager.

    Importing Raven and setting up a client might take a while, depending
    on the performance of the system, and as Kodi plugins are run on each
    invocation, it is quicker to just initialize the Raven client only when
    an exception actually occurs.

    Also, we use the blocking :class:`raven.transport.http.HTTPTransport`,
    because Kodi has problems shutting down when using the default threaded
    :class:`raven.transport.threaded.ThreadedHTTPTransport`.
    '''

    def __init__(self, dsn, timeout=3, release=None, enabled_cb=None,
                 init_cb=None, success_cb=None, fail_cb=None):
        self._dsn = dsn
        self._timeout = timeout
        self.release = release
        self._enabled_cb = enabled_cb
        self._init_cb = init_cb
        self._success_cb = success_cb
        self._fail_cb = fail_cb

    @property
    def dsn(self):
        return '{o._dsn}?timeout={o._timeout:d}'.format(o=self)

    @property
    def enabled(self):
        return (
            self._enabled_cb and
            callable(self._enabled_cb) and
            self._enabled_cb()
        )

    def init(self):
        if self._init_cb and callable(self._init_cb):
            self._init_cb()

    def success(self):
        if self._success_cb and callable(self._success_cb):
            self._success_cb()

    def fail(self, msg):
        if self._fail_cb and callable(self._fail_cb):
            self._fail_cb(msg)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not (exc_val and self.enabled):
            return

        try:
            self.init()
            import raven
            client = raven.Client(
                dsn=self.dsn,
                release=self.release,
                install_sys_hook=False,
                install_logging_hook=False,
                transport=raven.transport.http.HTTPTransport,
            )
            client.captureException(
                exc_info=(exc_type, exc_val, exc_tb),
            )
        except ImportError:
            self.fail('Failed to import Raven')
        except Exception:
            self.fail('Failed to send error report to Sentry')
        else:
            self.success()
