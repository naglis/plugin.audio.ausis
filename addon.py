# -*- coding: utf-7 -*-
from __future__ import unicode_literals

import os
import sys
import urllib

import xbmc as kodi
import xbmcaddon as kodiaddon
import xbmcgui as kodigui
import xbmcplugin as kodiplugin
import xbmcvfs as kodivfs

from resources.lib import database, tags, utils


class Ausis(object):

    def __init__(self, base_url, handle, addon):
        self.base_url = base_url
        self.handle = handle
        self.addon = addon

    def _build_url(self, **kwargs):
        '''Build and returns a plugin  URL.'''
        return '%s?%s' % (
            self.base_url, urllib.urlencode(utils.encode_values(kwargs))
        )

    def _t(self, string_id):
        return self.addon.getLocalizedString(string_id)

    @property
    def db_path(self):
        kodi_db_dir = kodi.translatePath('special://database')
        return os.path.join(kodi_db_dir, 'ausis.db')

    def log(self, msg, level=kodi.LOGDEBUG):
        log_enabled = (
            self.addon.getSetting('logging_enabled').lower() == 'true' or not
            level == kodi.LOGDEBUG)
        if log_enabled:
            msg = ('%s: %s' % (
                self.addon.getAddonInfo('id'), msg)).encode('utf-8')
            kodi.log(msg=msg, level=level)

    def run(self, args):
        mode = args.get('mode') or 'main'
        mode_handler = 'mode_%s' % mode
        if hasattr(self, mode_handler):
            return getattr(self, mode_handler)(args)
        else:
            self.log(
                'Plugin called with unknown mode: %s' % mode,
                level=kodi.LOGERROR,
            )

    def _prepare_audiofile_listitem(self, audiobook, item):
        cover = audiobook[b'cover_path']
        audiobook_path = audiobook[b'path']
        if cover:
            cover = os.path.join(audiobook_path, cover)
        fanart = audiobook[b'fanart_path']
        if fanart:
            fanart = os.path.join(audiobook_path, fanart)
        li = kodigui.ListItem(item[b'title'])
        li.setInfo('music', {
            'tracknumber': item[b'sequence'],
            'duration': int(item[b'duration']),
            'album': audiobook[b'title'],
            'artist': audiobook[b'author'],
            'title': item[b'title'],
            'genre': 'Audiobook',
            'comment': 'ausis:item:%d' % item[b'id'],
        })
        li.setArt({
            'thumb': cover,
            'icon': cover,
            'fanart': fanart,
        })
        return li

    def mode_main(self, args):
        directory = utils.decode_arg(
            self.addon.getSetting('audiobook_directory'))
        db = database.AudioBookDB.get_db(self.db_path)
        audiobooks = db.get_all_audiobooks()
        if not directory and not audiobooks:
            kodigui.Dialog().ok(self._t(30000), self._t(30001))
            return
        elif directory and not audiobooks and ask_to_scan:
            dialog = kodigui.Dialog()
            scan_now = dialog.yesno(self._t(30008), line1=self._t(30009),
                line2=self._t(30010), yeslabel=self._t(30011),
                nolabel=self._t(30012)
            )
            if scan_now:
                kodi.executebuiltin(
                    'RunPlugin(%s)' % self._build_url(mode='scan')
                )
                return
        for audiobook in audiobooks:
            cover = audiobook[b'cover_path']
            if cover:
                cover = os.path.join(audiobook[b'path'], cover)
            fanart = audiobook[b'fanart_path']
            if fanart:
                fanart = os.path.join(audiobook[b'path'], fanart)
            url = self._build_url(
                mode='audiobook', audiobook_id=audiobook[b'id'])
            li = kodigui.ListItem(audiobook[b'title'], iconImage=cover)
            if fanart:
                li.setProperty('Fanart_Image', fanart)
            kodiplugin.addDirectoryItem(
                handle=self.handle, url=url, listitem=li, isFolder=True)
        kodiplugin.endOfDirectory(self.handle)

    def mode_audiobook(self, args):
        audiobook_id = args.get('audiobook_id')
        db = database.AudioBookDB.get_db(self.db_path)
        if audiobook_id:
            audiobook, items = db.get_audiobook(audiobook_id)
            cover = audiobook[b'cover_path']
            if cover:
                cover = os.path.join(audiobook[b'path'], cover)
            fanart = audiobook[b'fanart_path']
            if fanart:
                fanart = os.path.join(audiobook[b'path'], fanart)
            bookmark = db.get_audiobook_last_bookmark(audiobook_id)
            if bookmark:
                self.log(str(bookmark))
                url = self._build_url(
                    mode='resume', bookmark_id=bookmark[b'id'])
                position = utils.format_duration(bookmark[b'position'])
                li = kodigui.ListItem('Resume (%s)' % position)
                kodiplugin.addDirectoryItem(
                    handle=self.handle,
                    url=url,
                    listitem=li,
                    isFolder=False,
                )
            for item in items:
                url = self._build_url(mode='play', audiofile_id=item[b'id'])
                li = self._prepare_audiofile_listitem(audiobook, item)
                kodiplugin.addDirectoryItem(
                    handle=self.handle,
                    url=url,
                    listitem=li,
                    isFolder=False,
                )
            kodiplugin.endOfDirectory(self.handle)
        else:
            self.log('No audiobook ID provided!', level=kodi.LOGERROR)

    def mode_play(self, args):
        audiofile_id = args.get('audiofile_id')
        db = database.AudioBookDB.get_db(self.db_path)
        if audiofile_id:
            audiobook, items = db.get_remaining_audiofiles(audiofile_id)
            audiobook_path = audiobook[b'path']
            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()
            for item in items:
                li = self._prepare_audiofile_listitem(audiobook, item)
                url = os.path.join(audiobook_path, item[b'file_path'])
                playlist.add(url, li)
            kodi.Player().play(playlist)
        else:
            self.log('No audiofile ID provided!', level=kodi.LOGERROR)

    def mode_resume(self, args):
        bookmark_id = args.get('bookmark_id')
        db = database.AudioBookDB.get_db(self.db_path)
        if bookmark_id:
            bookmark = db.get_bookmark(bookmark_id)
            if not bookmark:
                return
            audiofile_id = bookmark[b'audiofile_id']
            audiobook, items = db.get_remaining_audiofiles(audiofile_id)
            audiobook_path = audiobook[b'path']
            playlist = kodi.PlayList(kodi.PLAYLIST_MUSIC)
            playlist.clear()
            for idx, item in enumerate(items):
                li = self._prepare_audiofile_listitem(audiobook, item)
                # if idx == 0:
                    # li.setProperty(
                        # 'StartOffset', '%.2f' % bookmark[b'position'])
                url = os.path.join(audiobook_path, item[b'file_path'])
                playlist.add(url, li)
            player = kodi.Player()
            player.play(playlist)
            kodi.sleep(500)
            player.seekTime(bookmark[b'position'])
        else:
            self.log('No bookmark ID provided!', level=kodi.LOGERROR)

    def mode_scan(self, args):
        directory = utils.decode_arg(
            self.addon.getSetting('audiobook_directory'))
        if not directory:
            kodigui.Dialog().ok(self._t(30000), self._t(30001))
            return

        dialog = kodigui.DialogProgressBG()
        dialog.create('ausis', self._t(30007))

        dirs, _ = map(utils.decode_list, kodivfs.listdir(directory))
        total_dirs = len(dirs)

        db = database.AudioBookDB.get_db(self.db_path)

        for idx, subdir in enumerate(dirs, start=1):
            if db.audiobook_exists(subdir):
                self.log('Audiobook: %s already exists, skipping.' % subdir)
                continue
            abs_path = utils.encode_arg(os.path.join(directory, subdir))
            audiofiles = map(utils.decode_arg, utils.ifind_audio(abs_path))

            progress = int(100.0 * idx / total_dirs)
            dialog.update(progress)

            if not audiofiles:
                self.log('Subdirectory: %s contains no audiofiles' % abs_path)
                continue

            self.log('Subdirectory: %s contains: %d audiofiles' %
                     (utils.decode_arg(abs_path), len(audiofiles)))

            cover_files = list(utils.ifind_cover(abs_path))
            cover = utils.decode_arg(cover_files[0]) if cover_files else None
            fanart_files = list(utils.ifind_fanart(abs_path))
            fanart = utils.decode_arg(fanart_files[0]) if fanart_files else None

            items, authors, albums = [], set(), set()
            for f in sorted(audiofiles):
                # self.log('Getting tags of file: %s' % f)
                file_tags = tags.get_tags(f)
                if file_tags.album:
                    albums.add(file_tags.album)
                if file_tags.artist:
                    authors.add(file_tags.artist)
                # self.log(
                    # 'Item: %s, duration: %s' % (
                        # file_tags.title, file_tags.duration)
                # )
                items.append((file_tags.title, f, file_tags.duration))
            title = albums.pop() if albums else subdir

            if authors:
                author = authors.pop()
            else:
                # self.log('Unknown artist: %s' % subdir)
                continue

            db.add_audiobook(
                author, title, subdir, items, cover_path=cover,
                fanart_path=fanart,
            )

        self.log('Scan finished')
        dialog.close()


def main():
    addon = kodiaddon.Addon(id='plugin.audio.ausis')
    base_url, handle = sys.argv[0], int(sys.argv[1])
    args = utils.parse_query(sys.argv[2][1:])
    Ausis(base_url, handle, addon).run(args)

if __name__ == '__main__':
    main()
