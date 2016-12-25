# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib

import xbmc as kodi
import xbmcaddon as kodiaddon

from resources.lib import common
from resources.lib.db import (
    Audiobook,
    Audiofile,
    Bookmark,
    DB_FILE_NAME,
    database,
)

DB_PATH = common.get_db_path(DB_FILE_NAME)


class AudioBookPlayer(kodi.Player):
    '''Customized player which stores bookmarks.'''

    def _bookmark(self):
        '''
        Adds a bookmark on the currently playing audiofile.

        Currently, we store the audiofile's ID in the comment of each
        :class:`xbmcgui.ListItem` and use it to get the currently
        playing audiofile.
        '''
        try:
            current = self.getMusicInfoTag()
            position = self.getTime()
        except RuntimeError:
            pass
        else:
            if not current:
                return
            data = common.parse_comment(current.getComment())
            audiofile_id, offset = data.get('item'), data.get('offset') or 0
            if not audiofile_id:
                return
            position = offset + position
            with database.transaction():
                bookmark = Bookmark.create(
                    audiofile_id=audiofile_id, position=position)
                kodi.log('Added bookmark: %d at: %s' % (
                    bookmark.id, position))

    def onPlayBackStarted(self):
        self._bookmark()

    def onPlayBackPaused(self):
        self._bookmark()

    def onPlayBackResumed(self):
        self._bookmark()

    def onPlayBackSeek(self, time, seek_offset):
        self._bookmark()

    def onPlayBackEnded(self):
        self._bookmark()

    def onPlayBackStopped(self):
        self._bookmark()


def main():
    database.init(DB_PATH)
    database.connect()
    database.create_tables([Audiobook, Audiofile, Bookmark], True)
    monitor = kodi.Monitor()
    player = AudioBookPlayer()  # noqa

    def enabled_cb():
        addon = kodiaddon.Addon(id='plugin.audio.ausis')
        return addon.getSetting('send_crash_reports').lower() == 'true'

    raven = common.LazyRavenClient(
        common.SENTRY_URL,
        enabled_cb=enabled_cb,
    )
    with raven, contextlib.closing(database):
        while not monitor.abortRequested():
            if monitor.waitForAbort(10):
                break
    del player
    del monitor


if __name__ == '__main__':
    main()
