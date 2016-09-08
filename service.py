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

    def __init__(self, *args, **kwargs):
        super(AudioBookPlayer, self).__init__(*args, **kwargs)
        self.was_playing_audio = False
        self._current = None
        self._last_known_position = 0.0
        kodi.log('Started ausis AudioBookPlayer')

    def set_connection(self, conn):
        self._db = conn

    def _bookmark(self):
        if not self.was_playing_audio or not self._db:
            return
        try:
            current = self.getMusicInfoTag()
            position = self.getTime()
        except RuntimeError:
            current = self._current
            position = self._last_known_position
        finally:
            if not current:
                return
            audiofile_id = parse_id(current.getComment())
            if not audiofile_id:
                return
            with self._db:
                cr = self._db.cursor()
                bookmark_id = db.add_bookmark(cr, audiofile_id, position)
                if bookmark_id:
                    kodi.log('Added bookmark: %d at: %s' % (
                        bookmark_id, position))
                else:
                    kodi.log('Failed to add bookmark')

    def onPlayBackStarted(self):
        is_audio = self.isPlayingAudio()
        self.was_playing_audio = is_audio
        self._last_known_position = self.getTime()
        self._current = self.getMusicInfoTag() if is_audio else None
        kodi.log('Playback started')
        self._bookmark()

    def onPlayBackPaused(self):
        self._last_known_position = self.getTime()
        kodi.log('Playback paused')
        self._bookmark()

    def onPlayBackResumed(self):
        self._last_known_position = self.getTime()
        kodi.log('Playing resumed')
        self._bookmark()

    def onPlayBackSeek(self, time, seek_offset):
        self._last_known_position = time
        kodi.log('User seeked')
        self._bookmark()

    def onPlayBackEnded(self):
        self._last_known_position = self.getTime()
        kodi.log('Playback ended')
        self._bookmark()

    def onPlayBackStopped(self):
        kodi.log('Playback stopped')
        self._bookmark()


def main():
    monitor = kodi.Monitor()
    database = db.AudioBookDB(common.get_db_path(db.DB_FILE_NAME))
    player = AudioBookPlayer()  # noqa
    with contextlib.closing(database.get_conn()) as conn:
        player.set_connection(conn)
        while not monitor.abortRequested():
            if monitor.waitForAbort(10):
                break
    del player
    del monitor

if __name__ == '__main__':
    main()
