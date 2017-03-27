# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import operator
import sys
import time

import xbmc as kodi
import xbmcaddon as kodiaddon
import xbmcgui as kodigui
import xbmcplugin as kodiplugin

from resources.lib import common, utils
from resources.lib.db import (
    AusisDatabase,
    DB_FILE_NAME,
)

by_file = operator.itemgetter('file')


class Ausis(common.KodiPlugin):

    _strings = {
        'ausis': 30008,
        'yes': 30011,
        'no': 30012,
        'resume_latest': 30013,
        'resume_furthest': 30015,
        'remove_confirm_msg': 30016,
        'are_you_sure': 30017,
        'remove': 30018,
    }

    def __init__(self, base_url, handle, addon, db):
        super(Ausis, self).__init__(base_url, handle, addon)
        self._db = db

    @property
    def db(self):
        return self._db

    def _prepare_bookmark_listitem(self, string_id, bookmark):
        url = self._build_url(mode='resume', bookmark_id=bookmark.id)
        position = utils.format_duration(bookmark.position)
        li = kodigui.ListItem(
            common.italic(
                self._t(string_id) % (bookmark.audiofile.title, position)
            )
        )
        return dict(handle=self._handle, url=url, listitem=li, isFolder=False)

    def mode_album_bookmarks(self, args):
        album_id = args.get('album_id')
        if album_id is None:
            return
        bookmarks = self.db.get_album_bookmarks(album_id)

        for bookmark in bookmarks:
            url = self._build_url(
                mode='resume', bookmark_id=bookmark.id)
            song_info = common.json_rpc(
                'AudioLibrary.GetSongDetails',
                songid=bookmark.song_id,
                properties=[
                    'artist',
                    'title',
                    'duration',
                    'thumbnail',
                    'album',
                ],
            ).get('result', {}).get('songdetails', {})
            if not song_info:
                continue

            li = kodigui.ListItem(
                u'[{bookmark.name}] {title} ({position})'.format(
                    position=utils.format_duration(bookmark.position),
                    bookmark=bookmark,
                    **song_info),
                iconImage=song_info.get('thumbnail'),
            )
            li.setInfo('music', {
                'duration': song_info.get('duration', 0),
                'artist': u', '.join(song_info.get('artist', [])),
                'album': song_info.get('album'),
                'genre': 'Audiobook',
            })
            # last_played = utils.parse_datetime_str(audiobook.date_last_played)
            # li.setInfo('video', {
                # 'dateadded': audiobook.date_added.strftime(
                    # common.DATETIME_FORMAT),
                # 'lastplayed': last_played.strftime(
                    # common.DATETIME_FORMAT) if last_played else None,
            # })
            # if audiobook.fanart:
                # li.setProperty(
                    # 'Fanart_Image',
                    # os.path.join(directory, audiobook.fanart_path),
                # )
            # li.addContextMenuItems([
                # (self._t('remove'), 'RunPlugin(%s)' % self._build_url(
                    # mode='remove', audiobook_id=audiobook.id)),
            # ])
            kodiplugin.addDirectoryItem(
                handle=self._handle,
                url=url,
                listitem=li,
                isFolder=False,
                # totalItems=total_books,
            )
        kodiplugin.endOfDirectory(self._handle)

    def mode_main(self, args):
        # bms = self.db.get_all_bookmarks()
        albums = self.db.get_albums()
        self.log('%s' % albums)
        for bookmark in albums:
            # url = self._build_url(
                # mode='album_bookmarks', bookmark_id=bookmark.id)
            url = self._build_url(
                mode='album_bookmarks', album_id=bookmark.album_id)
            album_info = common.json_rpc(
                'AudioLibrary.GetAlbumDetails',
                albumid=bookmark.album_id,
                properties=[
                    'title',
                    'artist',
                    'fanart',
                    'thumbnail',
                    'dateadded',
                ],
            ).get('result', {}).get('albumdetails', {})
            self.log('%s' % album_info)
            if not album_info:
                return
            # song_info = common.json_rpc(
                # 'AudioLibrary.GetSongDetails', songid=bookmark.song_id, properties=[
                    # 'artist', 'title', 'duration', 'thumbnail', 'album']).get('result', {}).get('songdetails', {})
            # if not song_info:
                # continue

            li = kodigui.ListItem(
                album_info['title'],
                # u'{album} - {title} [{bookmark.name}] ({bookmark.position}s)'.format(
                    # bookmark=bookmark, **song_info),
                # iconImage=song_info.get('thumbnail'),
                iconImage=album_info.get('thumbnail'),
            )
            li.setInfo('music', {
                # 'duration': song_info.get('duration', 0),
                'artist': u', '.join(album_info.get('artist', [])),
                # 'album': song_info.get('album'),
                'genre': 'Audiobook',
            })
            # last_played = utils.parse_datetime_str(audiobook.date_last_played)
            # li.setInfo('video', {
                # 'dateadded': audiobook.date_added.strftime(
                    # common.DATETIME_FORMAT),
                # 'lastplayed': last_played.strftime(
                    # common.DATETIME_FORMAT) if last_played else None,
            # })
            # if audiobook.fanart:
                # li.setProperty(
                    # 'Fanart_Image',
                    # os.path.join(directory, audiobook.fanart_path),
                # )
            # li.addContextMenuItems([
                # (self._t('remove'), 'RunPlugin(%s)' % self._build_url(
                    # mode='remove', audiobook_id=audiobook.id)),
            # ])
            kodiplugin.addDirectoryItem(
                handle=self._handle,
                url=url,
                listitem=li,
                isFolder=True,
                # totalItems=total_books,
            )
        kodiplugin.endOfDirectory(self._handle)

    def mode_audiobook(self, args):
        pass
        '''
        for sort_method in common.AUDIOFILE_SORT_METHODS:
            kodiplugin.addSortMethod(self._handle, sort_method)
        audiobook_id = args.get('audiobook_id')
        if audiobook_id:
            audiobook_dir = utils.decode_arg(
                self._addon.getSetting('audiobook_directory'))
            audiobook = Audiobook.get(Audiobook.id == audiobook_id)
            bookmarks = audiobook.bookmarks
            if bookmarks:
                latest = utils.latest_bookmark(bookmarks)
                furthest = utils.furthest_bookmark(bookmarks)
                kodiplugin.addDirectoryItem(
                    **self._prepare_bookmark_listitem('resume_latest', latest)
                )
                if not latest == furthest:
                    kodiplugin.addDirectoryItem(
                        **self._prepare_bookmark_listitem(
                            'resume_furthest', furthest)
                    )

            for item in audiobook.audiofiles:
                url = self._build_url(mode='play', audiofile_id=item.id)
                li = common.prepare_audiofile_listitem(
                    audiobook_dir, audiobook, item)
                kodiplugin.addDirectoryItem(
                    handle=self._handle,
                    url=url,
                    listitem=li,
                    isFolder=False,
                    totalItems=len(audiobook.audiofiles),
                )
            kodiplugin.endOfDirectory(self._handle)
        else:
            self.log('No audiobook ID provided!', level=kodi.LOGERROR)
        '''

    def mode_play(self, args):
        pass
        '''
        audiofile_id = args.get('audiofile_id')
        if audiofile_id:
            audiobook_dir = utils.decode_arg(
                self._addon.getSetting('audiobook_directory'))
            audiofile = Audiofile.get(Audiofile.id == audiofile_id)
            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()
            for item in audiofile.get_remaining():
                li = common.prepare_audiofile_listitem(
                    audiobook_dir, audiofile.audiobook, item)
                url = os.path.join(audiobook_dir, item.path)
                playlist.add(url, li)
            kodi.Player().play(playlist)
        else:
            self.log('No audiofile ID provided!', level=kodi.LOGERROR)
        '''

    def mode_resume(self, args):
        bookmark_id = args.get('bookmark_id')
        if bookmark_id:
            bookmark = self.db.get_bookmark(bookmark_id)
            if not bookmark:
                return
            album_songs = sorted(common.json_rpc(
                'AudioLibrary.GetSongs',
                properties=[
                    'file',
                ],
                filter={
                    'albumid': bookmark.album_id,
                },
            ).get('result', {}).get('songs', []), key=by_file)

            # filtered = []
            # found = False
            # for song in album_songs:
                # if song['songid'] == bookmark.song_id:
                    # found = True
                # if found:
                    # filtered.append(song)


            # current = bookmark.audiofile
            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()
            playlist_id = playlist.getPlayListId()
            playlist_pos, offset = -1, 0
            items = []
            for idx, item in enumerate(album_songs):
                if item['songid'] == bookmark.song_id:
                    offset = max(0.0, bookmark.position)
                    playlist_pos = idx
                items.append({
                    'songid':  item['songid'],
                })
            resp = common.json_rpc(
                'Playlist.Add',
                playlistid=playlist_id,
                item=items
            )
            self.log('%s' % resp)
            player_id = common.get_audio_player_id()
            self.log('Player ID: %s' % player_id)
            if player_id is not None:
                common.json_rpc(
                    'Player.GoTo', playerid=player_id, to=playlist_pos)
                common.json_rpc(
                    'Player.Seek',
                    playerid=player_id,
                    value={
                        'seconds': int(offset),
                    },
                )
            else:
                p = kodi.Player()
                p.playselected(playlist_pos)

                # XXX: this is a nasty hack
                # TODO(naglis): search for alternatives
                i = 0
                while i < 20 and not p.isPlaying():
                    time.sleep(.05)
                    i += 1
                p.seekTime(offset)
                # li = common.prepare_audiofile_listitem(
                    # audiobook_dir, current.audiobook, item,
                    # data={'offset': offset}
                # )
                # if offset:
                    # li.setProperty('StartOffset', '{0:.2f}'.format(offset))
                # url = os.path.join(audiobook_dir, item.path)
                # playlist.add(url, li)
            # player = kodi.Player()
            # player.play(playlist)
        # else:
            # self.log('No bookmark ID provided!', level=kodi.LOGERROR)


def main():
    addon = kodiaddon.Addon(id='plugin.audio.ausis')
    base_url, handle = sys.argv[0], int(sys.argv[1])

    args = utils.parse_query(sys.argv[2][1:])
    db_filename = common.get_db_path(DB_FILE_NAME)
    with AusisDatabase(db_filename) as db:
        Ausis(base_url, handle, addon, db).run(args)


if __name__ == '__main__':
    main()
