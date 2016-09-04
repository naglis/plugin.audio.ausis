# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re

import xbmc as kodi

import database

ITEM_PATTERN = re.compile(r'(?x)^ausis:item:(?P<id>\d+)$')


def parse_id(comment):
    m = ITEM_PATTERN.match(comment)
    if m is not None:
        return int(m.group('id'))


def get_db_path():
    kodi_db_dir = kodi.translatePath('special://database')
    return os.path.join(kodi_db_dir, 'ausis.db')


class AudioBookPlayer(kodi.Player):

    def __init__(self, *args, **kwargs):
        super(AudioBookPlayer, self).__init__(*args, **kwargs)
        self.was_playing_audio = False
        self._current = None
        self._last_known_position = 0.0
        self._db = database.AudioBookDB.get_db(get_db_path())
        kodi.log('Started ausis AudioBookPlayer')

    def _bookmark(self):
        if not self.was_playing_audio:
            return
        try:
            current = self.getMusicInfoTag()
            position = self.getTime()
        except RuntimeError:
            current = self._current
            position = self._last_known_position
        finally:
            if current:
                audiofile_id = parse_id(current.getComment())
                if audiofile_id is not None:
                    bookmark_id = self._db.add_bookmark(audiofile_id, position)
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
    player = AudioBookPlayer()
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break


if __name__ == '__main__':
    main()
