# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import operator
import os
import sys
import time

import xbmc as kodi
import xbmcaddon as kodiaddon
import xbmcgui as kodigui
import xbmcplugin as kodiplugin

from resources.lib import common, tags, scan, utils
from resources.lib.db import (
    Audiobook,
    Audiofile,
    Bookmark,
    DB_FILE_NAME,
    database,
)

# by_label = operator.itemgetter('file')
def by_label(item):
    return item.get('file')


class Ausis(common.KodiPlugin):

    _strings = {
        'need_config': 30000,
        'dir_not_set': 30001,
        'scanning': 30007,
        'ausis': 30008,
        'library_empty_msg': 30009,
        'scan_now?': 30010,
        'yes': 30011,
        'no': 30012,
        'resume_latest': 30013,
        'unknown_author': 30014,
        'resume_furthest': 30015,
        'remove_confirm_msg': 30016,
        'are_you_sure': 30017,
        'remove': 30018,
    }

    def __init__(self, base_url, handle, addon):
        super(Ausis, self).__init__(base_url, handle, addon)

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
        # directory = utils.decode_arg(
            # self._addon.getSetting('audiobook_directory'))

        # Here we query on audiobook, audiofile and bookmark tables.
        # This is done in a raw query in order to decrease the number of
        # queries when calculating audiobook total duration and last played
        # position when called via peewee ORM.
        # audiobooks = Audiobook.raw('''
# SELECT
    # ab.*,
    # SUM(af.duration) AS total_duration,
    # MAX(
        # (
        # SELECT
            # MAX(b.date_added)
        # FROM
            # bookmark AS b
        # WHERE
            # b.audiofile_id = af.id
        # )
    # ) AS date_last_played
# FROM
    # audiobook AS ab
# INNER JOIN
    # audiofile AS af
# ON
    # ab.id = af.audiobook_id
# GROUP BY
    # af.audiobook_id;''').execute()

        # total_books = len(audiobooks)
        # library_is_empty = not bool(total_books)

        # if not directory and library_is_empty:
            # kodigui.Dialog().ok(self._t('need_config'), self._t('dir_not_set'))
            # return
        # elif directory and library_is_empty:
            # dialog = kodigui.Dialog()
            # scan_now = dialog.yesno(
                # self._t('ausis'), line1=self._t('library_empty_msg'),
                # line2=self._t('scan_now?'), yeslabel=self._t('yes'),
                # nolabel=self._t('no')
            # )
            # if scan_now:
                # kodi.executebuiltin(
                    # 'RunPlugin(%s)' % self._build_url(mode='scan')
                # )
                # return

        # for sort_method in common.AUDIOBOOK_SORT_METHODS:
            # kodiplugin.addSortMethod(self._handle, sort_method)

        # bookmarks = Bookmark.select()
        for bookmark in Bookmark.select():
            url = self._build_url(
                mode='resume', bookmark_id=bookmark.id)
            song_info = common.json_rpc(
                'AudioLibrary.GetSongDetails', songid=bookmark.song_id, properties=[
                    'artist', 'title', 'duration', 'thumbnail', 'album']).get('result', {}).get('songdetails', {})
            if not song_info:
                continue
            self.log('%s' % song_info, level=kodi.LOGERROR)

            li = kodigui.ListItem(
                u'{album} - {title} [{bookmark.name}] ({bookmark.position}s)'.format(
                    bookmark=bookmark, **song_info),
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

    def mode_audiobook(self, args):
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

    def mode_play(self, args):
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

    def mode_resume(self, args):
        # audiobook_dir = utils.decode_arg(
            # self._addon.getSetting('audiobook_directory'))
        bookmark_id = args.get('bookmark_id')
        if bookmark_id:
            bookmark = Bookmark.get(Bookmark.id == bookmark_id)
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
            ).get('result', {}).get('songs', []), key=by_label)

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
            self.log('%s' % resp, level=kodi.LOGERROR)
            player_id = common.get_audio_player_id()
            self.log('Player ID: %s' % player_id, level=kodi.LOGERROR)
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
                while i < 10 and not p.isPlaying():
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

    def mode_remove(self, args):
        audiobook_id = args.get('audiobook_id')
        if audiobook_id:
            audiobook = Audiobook.get(Audiobook.id == audiobook_id)
            dialog = kodigui.Dialog()
            confirmed = dialog.yesno(
                self._t('ausis'),
                line1=self._t('remove_confirm_msg') % audiobook.title,
                line2=self._t('are_you_sure'), yeslabel=self._t('yes'),
                nolabel=self._t('no')
            )
            if confirmed:
                audiobook.delete_instance()
                kodi.executebuiltin('Container.Refresh()')
        else:
            self.log('No audiobook ID provided!', level=kodi.LOGERROR)

    def mode_scan(self, args):
        directory = self._addon.getSetting('audiobook_directory')
        if not directory:
            kodigui.Dialog().ok(self._t('need_config'), self._t('dir_not_set'))
            return

        dialog = kodigui.DialogProgressBG()
        dialog.create('ausis', self._t('scanning'))
        try:
            for subdir, m in scan.scan(directory, progress_cb=dialog.update):
                # Check if audiobook at this path is already in the database.
                u_subdir = utils.decode_arg(subdir)
                audiobook = Audiobook.from_path(u_subdir)
                if audiobook:
                    self.log('Audiobook at path: %s already exists in '
                             'the library (ID: %s)' % (u_subdir, audiobook.id))
                else:
                    audiofiles = sorted(m.get('audio', []))
                    if not audiofiles:
                        self.log(
                            'Subdirectory: %s contains no audiofiles' %
                            u_subdir)
                        continue
                    self.log('Subdirectory: %s contains: %d audiofiles' %
                             (u_subdir, len(audiofiles)))
                    items, authors, albums = [], set(), set()
                    for fn in audiofiles:
                        abs_path = os.path.join(directory, subdir, fn)
                        file_tags = tags.get_tags(abs_path)
                        if file_tags.album:
                            albums.add(file_tags.album)
                        if file_tags.artist:
                            authors.add(file_tags.artist)
                        size = os.path.getsize(abs_path)
                        items.append((
                            file_tags.title,
                            utils.decode_arg(fn),
                            file_tags.duration,
                            size,
                        ))
                    title = albums.pop() if albums else u_subdir

                    if authors:
                        author = authors.pop()
                    else:
                        author = self._t('unknown_author')

                    audiobook = Audiobook.create(
                        author=author, title=title,
                        path=u_subdir)
                    for idx, (title, path, duration, size) in enumerate(items):
                        Audiofile.create(
                            audiobook=audiobook, title=title, sequence=idx,
                            file_path=path, duration=duration, size=size)

                if not audiobook.cover:
                    covers = m.get('cover', [])
                    if covers:
                        audiobook.cover = utils.decode_arg(
                            utils.first_of(covers))
                        audiobook.save()
                if not audiobook.fanart:
                    fanarts = m.get('fanart', [])
                    if fanarts:
                        audiobook.fanart = utils.decode_arg(
                            utils.first_of(fanarts))
                        audiobook.save()
        except Exception as e:
            self.log(
                'There was an error during scan: %s' % e, level=kodi.LOGERROR)
            raise
        finally:
            self.log('Scan finished')
            dialog.close()


def main():
    addon = kodiaddon.Addon(id='plugin.audio.ausis')
    base_url, handle = sys.argv[0], int(sys.argv[1])
    ausis = Ausis(base_url, handle, addon)

    def enabled_cb():
        '''Callback to check if crash reports are enabled.'''
        return addon.getSetting('send_crash_reports').lower() == 'true'

    def fail_cb(msg=None):
        '''Callback for when sending the crash report to Sentry fails.'''
        if msg:
            ausis.log(msg, level=kodi.LOGERROR)

    args = utils.parse_query(sys.argv[2][1:])
    db_filename = common.get_db_path(DB_FILE_NAME)
    database.init(db_filename)
    database.connect()
    # database.create_tables([Audiobook, Audiofile, Bookmark], safe=True)
    database.create_tables([Bookmark], safe=True)
    # raven = common.LazyRavenClient(
        # common.SENTRY_URL,
        # release=addon.getAddonInfo('version'),
        # enabled_cb=enabled_cb,
        # fail_cb=fail_cb,
    # )
    # with raven, contextlib.closing(database), database.transaction():
    with  contextlib.closing(database), database.transaction():
        ausis.run(args)


if __name__ == '__main__':
    main()
