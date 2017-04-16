# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import operator
import sys

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
on_click_actions = {
    '0': 'resume_latest',
    '1': 'album_bookmarks',
}


class Ausis(common.KodiPlugin):

    _strings = {
        'remove_bookmarks': 30002,
        'remove_confirm_msg': 30003,
        'are_you_sure': 30004,
        'yes': 30005,
        'no': 30006,
        'show_all_bookmarks': 30009,
        'started': 30010,
        'paused': 30011,
        'resumed': 30012,
        'seeked': 30013,
        'ended': 30014,
        'stopped': 30015,
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

    def mode_main(self, args):
        albums = self.db.get_albums()

        mode = on_click_actions.get(
            self._addon.getSetting('on_audiobook_click'), 'resume_latest')

        for bookmark in albums:
            url = self._build_url(mode=mode, album_id=bookmark.album_id)
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
            if not album_info:
                continue

            last_played = datetime.datetime.fromtimestamp(bookmark.date_added)
            li = kodigui.ListItem(album_info['title'])

            li.setArt({
                'thumb': album_info.get('thumbnail'),
                'fanart': album_info.get('fanart'),
            })
            li.setInfo('music', {
                'artist': u', '.join(album_info.get('artist', [])),
                'album': album_info['title'],
                'genre': 'Audiobook',
                'lastplayed': last_played.strftime(common.DATETIME_FORMAT),
            })

            context_menu = [(
                self._t('remove_bookmarks'),
                'RunPlugin(%s)' % self._build_url(
                    mode='remove_album_bookmarks',
                    album_id=bookmark.album_id,
                ),
            )]
            li.addContextMenuItems(context_menu)

            kodiplugin.addDirectoryItem(
                handle=self._handle,
                url=url,
                listitem=li,
                isFolder=True,
                totalItems=len(albums),
            )
        kodiplugin.endOfDirectory(self._handle)

    def mode_album_bookmarks(self, args):
        album_id = args.get('album_id')

        if album_id is None:
            return kodi.log('album_id not set', level=kodi.LOGERROR)

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
                    'track',
                ],
            ).get('result', {}).get('songdetails', {})
            if not song_info:
                continue

            li = kodigui.ListItem(
                u'[{name}] {title} ({position})'.format(
                    name=self._t(bookmark.name),
                    position=utils.format_duration(bookmark.position),
                    **song_info),
                iconImage=song_info.get('thumbnail'),
            )
            li.setInfo('music', {
                'duration': song_info.get('duration', 0),
                'artist': u', '.join(song_info.get('artist', [])),
                'album': song_info.get('album'),
                'genre': 'Audiobook',
                'tracknumber': song_info.get('track'),
            })
            kodiplugin.addDirectoryItem(
                handle=self._handle,
                url=url,
                listitem=li,
                isFolder=False,
                totalItems=len(bookmarks),
            )
        kodiplugin.endOfDirectory(self._handle)

    def mode_resume(self, args):
        bookmark_id = args.get('bookmark_id')
        if bookmark_id:
            bookmark = self.db.get_bookmark(bookmark_id)
            if not bookmark:
                return kodi.log('Bookmark does not exist', level=kodi.LOGERROR)
            album_songs = sorted(common.json_rpc(
                'AudioLibrary.GetSongs',
                # TODO(naglis): add more fields
                properties=[
                    'file',
                    'artist',
                    'title',
                    'duration',
                    'year',
                ],
                filter={
                    'albumid': bookmark.album_id,
                },
            ).get('result', {}).get('songs', []), key=by_file)

            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()

            playlist_pos = -1
            for idx, item in enumerate(album_songs):
                offset = None

                li = kodigui.ListItem(item.get('title', ''))

                if item['songid'] == bookmark.song_id:
                    playlist_pos = idx
                    offset = max(0.0, bookmark.position)
                    li.setProperty('StartOffset', '{0:.2f}'.format(offset))

                music_info = {
                    'year': item.get('year'),
                    'artist': u', '.join(item.get('artist', [])),
                    'duration': item.get('duration'),
                    'title': item.get('title'),
                }

                if offset is not None:
                    music_info.update({
                        'comment': common.dump_comment({'offset': offset}),
                    })

                # TODO(naglis): add more fields
                # TODO(naglis): make nicer
                li.setInfo('music', music_info)

                playlist.add(item['file'], li)

            kodi.Player().play(playlist, startpos=playlist_pos)

    def mode_resume_latest(self, args):
        album_id = args.get('album_id')

        if album_id is None:
            return kodi.log('album_id not set', level=kodi.LOGERROR)

        latest_bookmark = utils.first_of(
            self.db.get_album_bookmarks(album_id))
        return self.mode_resume({
            'bookmark_id': latest_bookmark.id,
        })

    def mode_remove_album_bookmarks(self, args):
        album_id = args.get('album_id')

        if album_id is None:
            return kodi.log('album_id not set', level=kodi.LOGERROR)

        dialog = kodigui.Dialog()
        confirmed = dialog.yesno(
            self._t('remove_bookmarks'),
            line1=self._t('remove_confirm_msg'),
            line2=self._t('are_you_sure'),
            yeslabel=self._t('yes'),
            nolabel=self._t('no')
        )
        if confirmed:
            self.db.remove_album_bookmarks(album_id)
            kodi.executebuiltin('Container.Refresh()')


def main():
    addon = kodiaddon.Addon(id='plugin.audio.ausis')
    base_url, handle = sys.argv[0], int(sys.argv[1])

    args = utils.parse_query(sys.argv[2][1:])
    db_filename = common.get_db_path(DB_FILE_NAME)
    with AusisDatabase(db_filename) as db:
        Ausis(base_url, handle, addon, db).run(args)


if __name__ == '__main__':
    main()
