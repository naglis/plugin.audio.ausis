# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import os
import sys

import peewee
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
        'error': 30020,
        'sending_report': 30021,
        'report_sent': 30022,
        'report_sent_msg': 30023,
        'report_failed': 30024,
        'report_failed_msg': 30025,
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
        directory = utils.decode_arg(
            self._addon.getSetting('audiobook_directory'))

        audiobooks = Audiobook.select()
        audiofiles = Audiofile.select()
        audiobooks_with_files = peewee.prefetch(audiobooks, audiofiles)
        total_books = len(audiobooks_with_files)
        library_is_empty = not bool(total_books)

        if not directory and library_is_empty:
            kodigui.Dialog().ok(self._t('need_config'), self._t('dir_not_set'))
            return
        elif directory and library_is_empty:
            dialog = kodigui.Dialog()
            scan_now = dialog.yesno(
                self._t('ausis'), line1=self._t('library_empty_msg'),
                line2=self._t('scan_now?'), yeslabel=self._t('yes'),
                nolabel=self._t('no')
            )
            if scan_now:
                kodi.executebuiltin(
                    'RunPlugin(%s)' % self._build_url(mode='scan')
                )
                return

        for sort_method in common.AUDIOBOOK_SORT_METHODS:
            kodiplugin.addSortMethod(self._handle, sort_method)

        for audiobook in audiobooks_with_files:
            url = self._build_url(
                mode='audiobook', audiobook_id=audiobook.id)
            li = kodigui.ListItem(
                audiobook.title,
                iconImage=(
                    os.path.join(directory, audiobook.cover_path)
                    if audiobook.cover else None
                )
            )
            duration = sum(i.duration for i in audiobook.audiofiles_prefetch)
            li.setInfo('music', {
                'duration': duration,
                'artist': audiobook.author,
                'album': audiobook.title,
                'genre': 'Audiobook',
            })
            last_played = audiobook.last_played
            li.setInfo('video', {
                'dateadded': audiobook.date_added.strftime(
                    common.DATETIME_FORMAT),
                'lastplayed': last_played.strftime(
                    common.DATETIME_FORMAT) if last_played else None,
            })
            if audiobook.fanart:
                li.setProperty(
                    'Fanart_Image',
                    os.path.join(directory, audiobook.fanart_path),
                )
            li.addContextMenuItems([
                (self._t('remove'), 'RunPlugin(%s)' % self._build_url(
                    mode='remove', audiobook_id=audiobook.id)),
            ])
            kodiplugin.addDirectoryItem(
                handle=self._handle,
                url=url,
                listitem=li,
                isFolder=True,
                totalItems=total_books,
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

    def init_cb():
        '''Callback for when the crash report is being sent to Sentry.'''
        kodi.executebuiltin('ActivateWindow(Home)')
        kodigui.Dialog().notification(
            ausis._t('error'),
            ausis._t('sending_report'),
            icon=kodigui.NOTIFICATION_ERROR,
            time=4000,
            sound=True,
        )

    def success_cb():
        '''
        Callback for when the crash report is successfully sent to Sentry.
        '''
        kodigui.Dialog().notification(
            ausis._t('report_sent'),
            ausis._t('report_sent_msg'),
            icon=kodigui.NOTIFICATION_INFO,
            time=2000,
            sound=False,
        )

    def fail_cb(msg=None):
        '''Callback for when sending the crash report to Sentry fails.'''
        if msg:
            ausis.log(msg, level=kodi.LOGERROR)
        kodigui.Dialog().notification(
            ausis._t('report_failed'),
            ausis._t('report_failed_msg'),
            icon=kodigui.NOTIFICATION_ERROR,
            time=2000,
            sound=False,
        )

    args = utils.parse_query(sys.argv[2][1:])
    db_filename = common.get_db_path(DB_FILE_NAME)
    database.init(db_filename)
    database.connect()
    database.create_tables([Audiobook, Audiofile, Bookmark], safe=True)
    raven = common.LazyRavenClient(
        common.SENTRY_URL,
        release=addon.getAddonInfo('version'),
        enabled_cb=enabled_cb,
        init_cb=init_cb,
        success_cb=success_cb,
        fail_cb=fail_cb,
    )
    with raven, contextlib.closing(database), database.transaction():
        ausis.run(args)


if __name__ == '__main__':
    main()
