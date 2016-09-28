# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys

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


class Ausis(common.KodiPlugin):

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
        directory = utils.decode_arg(
            self._addon.getSetting('audiobook_directory'))
        audiobooks = Audiobook.select()
        if not directory and not audiobooks:
            kodigui.Dialog().ok(self._t(30000), self._t(30001))
            return
        elif directory and not audiobooks:
            dialog = kodigui.Dialog()
            scan_now = dialog.yesno(
                self._t(30008), line1=self._t(30009),
                line2=self._t(30010), yeslabel=self._t(30011),
                nolabel=self._t(30012)
            )
            if scan_now:
                kodi.executebuiltin(
                    'RunPlugin(%s)' % self._build_url(mode='scan')
                )
                return

        for sort_method in common.AUDIOBOOK_SORT_METHODS:
            kodiplugin.addSortMethod(self._handle, sort_method)

        for audiobook in audiobooks:
            url = self._build_url(
                mode='audiobook', audiobook_id=audiobook.id)
            li = kodigui.ListItem(
                audiobook.title,
                iconImage=(
                    os.path.join(directory, audiobook.cover_path)
                    if audiobook.cover else None
                )
            )
            li.setInfo('music', {
                'duration': audiobook.duration,
                'artist': audiobook.author,
                'album': audiobook.title,
                'genre': 'Audiobook',
            })
            li.setInfo('video', {
                'dateadded': audiobook.date_added.strftime(
                    common.DATETIME_FORMAT),
                'lastplayed': audiobook.last_played.strftime(
                    common.DATETIME_FORMAT),
            })
            if audiobook.fanart:
                li.setProperty(
                    'Fanart_Image',
                    os.path.join(directory, audiobook.fanart_path),
                )
            li.addContextMenuItems([
                (self._t(30018), 'RunPlugin(%s)' % self._build_url(
                    mode='remove', audiobook_id=audiobook.id)),
            ])
            kodiplugin.addDirectoryItem(
                handle=self._handle,
                url=url,
                listitem=li,
                isFolder=True,
                totalItems=len(audiobooks),
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
                    **self._prepare_bookmark_listitem(30013, latest)
                )
                if not latest == furthest:
                    kodiplugin.addDirectoryItem(
                        **self._prepare_bookmark_listitem(30015, furthest)
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
        audiobook_dir = utils.decode_arg(
            self._addon.getSetting('audiobook_directory'))
        bookmark_id = args.get('bookmark_id')
        if bookmark_id:
            bookmark = Bookmark.get(Bookmark.id == bookmark_id)
            if not bookmark:
                return
            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()
            current = bookmark.audiofile
            for item in current.get_remaining():
                offset = bookmark.position if item.id == current.id else 0.0
                li = common.prepare_audiofile_listitem(
                    audiobook_dir, current.audiobook, item,
                    data={'offset': offset}
                )
                if offset:
                    li.setProperty('StartOffset', '{0:.2f}'.format(offset))
                url = os.path.join(audiobook_dir, item.path)
                playlist.add(url, li)
            player = kodi.Player()
            player.play(playlist)
        else:
            self.log('No bookmark ID provided!', level=kodi.LOGERROR)

    def mode_remove(self, args):
        audiobook_id = args.get('audiobook_id')
        if audiobook_id:
            audiobook = Audiobook.get(Audiobook.id == audiobook_id)
            dialog = kodigui.Dialog()
            confirmed = dialog.yesno(
                self._t(30008),
                line1=self._t(30016) % audiobook.title,
                line2=self._t(30017), yeslabel=self._t(30011),
                nolabel=self._t(30012)
            )
            if confirmed:
                audiobook.delete_instance()
                kodi.executebuiltin('Container.Refresh()')
        else:
            self.log('No audiobook ID provided!', level=kodi.LOGERROR)

    def mode_scan(self, args):
        directory = self._addon.getSetting('audiobook_directory')
        if not directory:
            kodigui.Dialog().ok(self._t(30000), self._t(30001))
            return

        dialog = kodigui.DialogProgressBG()
        dialog.create('ausis', self._t(30007))
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
                        author = self._t(30014)

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
    try:
        base_url, handle = sys.argv[0], int(sys.argv[1])
        args = utils.parse_query(sys.argv[2][1:])
        db_filename = common.get_db_path(DB_FILE_NAME)
        database.init(db_filename)
        database.connect()
        database.create_tables([Audiobook, Audiofile, Bookmark], safe=True)
        with database.transaction():
            Ausis(base_url, handle, addon).run(args)
    except Exception:
        send_report = (
            addon.getSetting('send_crash_reports').lower() == 'true')
        if not send_report:
            raise

        # Send the crash report / inform the user.
        dialog = kodigui.Dialog()
        dialog.notification(
            addon.getLocalizedString(30020),
            addon.getLocalizedString(30021),
            icon=kodigui.NOTIFICATION_ERROR,
            time=4000,
            sound=True,
        )
        kodi.executebuiltin('ActivateWindow(Home)')
        sent = common.send_crash_report(
            release=addon.getAddonInfo('version'))
        if sent:
            dialog.notification(
                addon.getLocalizedString(30022),
                addon.getLocalizedString(30023),
                icon=kodigui.NOTIFICATION_INFO,
                time=2000,
                sound=False,
            )
    finally:
        try:
            database.close()
        except:
            pass

if __name__ == '__main__':
    main()
