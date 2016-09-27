# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys

import xbmc as kodi
import xbmcaddon as kodiaddon
import xbmcgui as kodigui
import xbmcplugin as kodiplugin

from resources.lib import common, db as database, tags, scan, utils


class Ausis(common.KodiPlugin):

    def __init__(self, base_url, handle, addon, db):
        super(Ausis, self).__init__(base_url, handle, addon)
        self._db = db

    @property
    def db(self):
        return self._db

    def _prepare_bookmark_listitem(self, string_id, bookmark):
        url = self._build_url(
            mode='resume', bookmark_id=bookmark[b'id'])
        position = utils.format_duration(bookmark[b'position'])
        li = kodigui.ListItem(
            common.italic(
                self._t(string_id) % (bookmark[b'title'], position)
            )
        )
        return dict(handle=self._handle, url=url, listitem=li, isFolder=False)

    def mode_main(self, args):
        directory = utils.decode_arg(
            self._addon.getSetting('audiobook_directory'))
        audiobooks = self.db.get_all_audiobooks()
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
            audiobook_id = audiobook[b'id']
            cover = audiobook[b'cover_path']
            if cover:
                cover = os.path.join(
                    directory, audiobook[b'path'], cover)
            fanart = audiobook[b'fanart_path']
            if fanart:
                fanart = os.path.join(
                    directory, audiobook[b'path'], fanart)
            url = self._build_url(
                mode='audiobook', audiobook_id=audiobook_id)
            li = kodigui.ListItem(audiobook[b'title'], iconImage=cover)
            info_labels = {
                'duration': int(audiobook[b'duration']),
                'artist': audiobook[b'author'],
                'album': audiobook[b'title'],
                'genre': 'Audiobook',
            }
            li.setInfo('music', info_labels)

            li.setInfo('video', {
                'dateadded': audiobook[b'date_added'].strftime(
                    common.DATETIME_FORMAT),
            })
            if audiobook[b'last_played']:
                li.setInfo('video', {
                    'lastplayed': audiobook[b'last_played'],
                })
            if fanart:
                li.setProperty('Fanart_Image', fanart)
            li.addContextMenuItems([
                (self._t(30018), 'RunPlugin(%s)' % self._build_url(
                    mode='remove', audiobook_id=audiobook_id)),
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
            audiobook, items = self.db.get_audiobook(audiobook_id)
            cover = audiobook[b'cover_path']
            if cover:
                cover = os.path.join(
                    audiobook_dir, audiobook[b'path'], cover)
            fanart = audiobook[b'fanart_path']
            if fanart:
                fanart = os.path.join(
                    audiobook_dir, audiobook[b'path'], fanart)

            bookmarks = self.db.get_audiobook_bookmarks(audiobook_id)
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

            for item in items:
                url = self._build_url(mode='play', audiofile_id=item[b'id'])
                li = common.prepare_audiofile_listitem(
                    audiobook_dir, audiobook, item)
                kodiplugin.addDirectoryItem(
                    handle=self._handle,
                    url=url,
                    listitem=li,
                    isFolder=False,
                    totalItems=len(items),
                )
            kodiplugin.endOfDirectory(self._handle)
        else:
            self.log('No audiobook ID provided!', level=kodi.LOGERROR)

    def mode_play(self, args):
        audiofile_id = args.get('audiofile_id')
        if audiofile_id:
            audiobook_dir = utils.decode_arg(
                self._addon.getSetting('audiobook_directory'))
            audiobook, items = self.db.get_remaining_audiofiles(audiofile_id)
            audiobook_path = audiobook[b'path']
            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()
            for item in items:
                li = common.prepare_audiofile_listitem(
                    audiobook_dir, audiobook, item)
                url = os.path.join(
                    audiobook_dir, audiobook_path, item[b'file_path'])
                playlist.add(url, li)
            kodi.Player().play(playlist)
        else:
            self.log('No audiofile ID provided!', level=kodi.LOGERROR)

    def mode_resume(self, args):
        audiobook_dir = utils.decode_arg(
            self._addon.getSetting('audiobook_directory'))
        bookmark_id = args.get('bookmark_id')
        if bookmark_id:
            bookmark = self.db.get_bookmark(bookmark_id)
            if not bookmark:
                return
            audiofile_id = bookmark[b'audiofile_id']
            audiobook, items = self.db.get_remaining_audiofiles(audiofile_id)
            audiobook_path = audiobook[b'path']
            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()
            for idx, item in enumerate(items):
                offset = 0.0 if idx > 0 else bookmark[b'position']
                li = common.prepare_audiofile_listitem(
                    audiobook_dir, audiobook, item, data={'offset': offset})
                if offset:
                    li.setProperty('StartOffset', '{0:.2f}'.format(offset))
                url = os.path.join(
                    audiobook_dir, audiobook_path, item[b'file_path'])
                playlist.add(url, li)
            player = kodi.Player()
            player.play(playlist)
        else:
            self.log('No bookmark ID provided!', level=kodi.LOGERROR)

    def mode_remove(self, args):
        audiobook_id = args.get('audiobook_id')
        if audiobook_id:
            audiobook, _ = self.db.get_audiobook(audiobook_id)
            dialog = kodigui.Dialog()
            confirmed = dialog.yesno(
                self._t(30008),
                line1=self._t(30016) % audiobook[b'title'],
                line2=self._t(30017), yeslabel=self._t(30011),
                nolabel=self._t(30012)
            )
            if confirmed:
                self.db.remove_audiobook(audiobook_id)
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
                audiobook_id = self.db.get_audiobook_by_path(u_subdir)
                if audiobook_id:
                    self.log('Audiobook at path: %s already exists in '
                             'the library (ID: %s)' % (u_subdir, audiobook_id))
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

                    audiobook_id = self.db.add_audiobook(
                        author, title, u_subdir, items)

                if not self.db.get_cover(audiobook_id):
                    covers = m.get('cover', [])
                    if covers:
                        self.db.set_cover(
                            audiobook_id,
                            utils.decode_arg(utils.first_of(covers)),
                        )
                if not self.db.get_fanart(audiobook_id):
                    fanarts = m.get('fanart', [])
                    if fanarts:
                        self.db.set_fanart(
                            audiobook_id,
                            utils.decode_arg(utils.first_of(fanarts)),
                        )
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
        db_filename = common.get_db_path(database.DB_FILE_NAME)
        with database.AusisDatabase(db_filename) as db:
            Ausis(base_url, handle, addon, db).run(args)
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

if __name__ == '__main__':
    main()
