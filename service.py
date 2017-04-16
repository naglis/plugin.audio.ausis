# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import xbmc as kodi
import xbmcaddon as kodiaddon

from resources.lib import common
from resources.lib.db import (
    AusisDatabase,
    DB_FILE_NAME,
)

addon = kodiaddon.Addon(id='plugin.audio.ausis')
DB_PATH = common.get_db_path(DB_FILE_NAME)


def get_audio_player_id():
    resp = common.json_rpc('Player.GetActivePlayers')
    for player in resp.get('result', []):
        if player.get('type') == 'audio':
            return player.get('playerid')


def get_current_info():
    player_id = get_audio_player_id()
    if player_id is not None:
        resp = common.json_rpc(
            'Player.GetItem',
            playerid=player_id,
            properties=[
                'albumid',
                'file',
            ],
        )
        return resp.get('result', {}).get('item', {})


class AudioBookPlayer(kodi.Player):
    '''Customized player which stores bookmarks.'''

    def _get_offset(self):
        try:
            info = self.getMusicInfoTag()
            extra_data = common.parse_comment(info.getComment() or '')
            return extra_data.get('offset') or 0.0
        except RuntimeError:
            return 0.0

    def _bookmark(self, name='other'):
        '''
        Adds a bookmark on the currently playing audiofile.

        Currently, we store the audiofile's ID in the comment of each
        :class:`xbmcgui.ListItem` and use it to get the currently
        playing audiofile.
        '''

        audiobook_dir = addon.getSetting('audiobook_directory')
        try:
            position = self.getTime()

            # The position when starting is sometimes negative.
            if name == 'started':
                position = max(0.0, position)

            current = get_current_info()
            if not current:
                return
            song_id, album_id, filename = map(
                current.get, ('id', 'albumid', 'file'))

            # Song is not from the music library.
            if not (song_id and album_id):
                return

            # File not from the audiobook directory.
            if (audiobook_dir and filename and not
                    filename.startswith(audiobook_dir)):
                return
            offset = self._get_offset()
        except RuntimeError:
            kodi.log('Runtime error')
        else:
            with AusisDatabase(DB_PATH) as db:
                bookmark_id = db.add_bookmark(
                    name, song_id, album_id, offset + position)
                kodi.log('Added bookmark of type: "%s" with ID %d at: %s' % (
                    name, bookmark_id, offset + position))

    def onPlayBackStarted(self):
        self._bookmark('started')

    def onPlayBackPaused(self):
        self._bookmark('paused')

    def onPlayBackResumed(self):
        self._bookmark('resumed')

    def onPlayBackSeek(self, time, seek_offset):
        self._bookmark('seeked')

    def onPlayBackEnded(self):
        self._bookmark('ended')

    def onPlayBackStopped(self):
        self._bookmark('stopped')


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
