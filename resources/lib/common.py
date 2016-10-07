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

# I know, I know... This is just mild obfuscation.
SENTRY_URL = (
    '68747470733a2f2f653532396430633836653434343931336161323263376166633639336'
    '23634313a3937636438383234393265663432393838366534313730376635633035636130'
    '4073656e7472792e696f2f313031383937').decode('hex')


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


def send_crash_report(release=None, timeout=3):
    # Importing Raven and setting up a client might take a while, depending
    # on the performance of the system, and as Kodi plugins are run on each
    # invocation, it is quicker to just initialize the Raven client only when
    # an exception actually occurs.

    # Also, we use the blocking :class:`raven.transport.http.HTTPTransport`,
    # because Kodi has problems shutting down when using the default threaded
    # :class:`raven.transport.threaded.ThreadedHTTPTransport`.
    success = False
    try:
        import raven
        client = raven.Client(
            dsn='%s?timeout=%d' % (SENTRY_URL, timeout),
            release=release,
            install_sys_hook=False,
            install_logging_hook=False,
            transport=raven.transport.http.HTTPTransport,
        )
        client.captureException()
    except ImportError:
        kodi.log('Failed to import Raven', level=kodi.LOGERROR)
    except Exception:
        kodi.log('Failed to send error report to Sentry', level=kodi.LOGERROR)
    else:
        success = True
    return success
