# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import re

import xbmc as kodi

from resources.lib import common, db

ITEM_PATTERN = re.compile(r'(?x)^ausis:item:(?P<id>\d+)$')


def parse_id(comment):
    m = ITEM_PATTERN.match(comment)
    if m is not None:
        return int(m.group('id'))


class AudioBookPlayer(kodi.Player):
    '''Customized player which stores bookmarks.'''

    def __init__(self, *args, **kwargs):
        super(AudioBookPlayer, self).__init__(*args, **kwargs)
        self._db_path = common.get_db_path(db.DB_FILE_NAME)

    def _bookmark(self):
        try:
            current = self.getMusicInfoTag()
            position = self.getTime()
        except RuntimeError:
            pass
        else:
            if not current:
                return
            audiofile_id = parse_id(current.getComment())
            if not audiofile_id:
                return
            database = db.AudioBookDB(self._db_path)
            with contextlib.closing(database.get_conn()) as conn, conn as conn:
                cr = conn.cursor()
                bookmark_id = db.add_bookmark(cr, audiofile_id, position)
                if bookmark_id:
                    kodi.log('Added bookmark: %d at: %s' % (
                        bookmark_id, position))
                else:
                    kodi.log('Failed to add bookmark')

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
    monitor = kodi.Monitor()
    player = AudioBookPlayer()  # noqa
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break
    del player
    del monitor

if __name__ == '__main__':
    main()
