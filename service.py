# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import xbmc as kodi

from resources.lib import common
from resources.lib.db import (
    AusisDatabase,
    DB_FILE_NAME,
)

DB_PATH = common.get_db_path(DB_FILE_NAME)


def get_current_id():
    player_id = common.get_audio_player_id()
    if player_id is not None:
        resp = common.json_rpc(
            'Player.GetItem',
            playerid=player_id,
            properties=[
                'albumid',
            ],
        )
        kodi.log('%s' % resp)
        return resp.get('result', {}).get('item', {})


class AudioBookPlayer(kodi.Player):
    '''Customized player which stores bookmarks.'''

    def _bookmark(self, name='other'):
        '''
        Adds a bookmark on the currently playing audiofile.

        Currently, we store the audiofile's ID in the comment of each
        :class:`xbmcgui.ListItem` and use it to get the currently
        playing audiofile.
        '''
        try:
            if name == 'started':
                position = 0.0
            else:
                position = self.getTime()
            current = get_current_id()
            if not current:
                return
            song_id, album_id = map(current.get, ('id', 'albumid'))
            if not (song_id and album_id):
                return
            kodi.log('%s' % current)
        except RuntimeError:
            kodi.log('Runtime error')
        else:
            # data = common.parse_comment(current.getComment())
            # audiofile_id, offset = data.get('item'), data.get('offset') or 0
            # kodi.log('Event at: %s with item: %s' % (position, track_url))
            # if not audiofile_id:
                # return
            # position = offset + position
            with AusisDatabase(DB_PATH) as db:
                bookmark_id = db.add_bookmark(
                    name, song_id, album_id, position)
                kodi.log('Added bookmark: %d at: %s' % (
                    bookmark_id, position))

    def onPlayBackStarted(self):
        self._bookmark('started')

    def onPlayBackPaused(self):
        self._bookmark('paused')

    # def onPlayBackResumed(self):
        # self._bookmark('resumed')

    # def onPlayBackSeek(self, time, seek_offset):
        # self._bookmark('seeked')

    # def onPlayBackEnded(self):
        # self._bookmark('ended')

    # def onPlayBackStopped(self):
        # self._bookmark('stopped')


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
