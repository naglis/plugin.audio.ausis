# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

import xbmc as kodi
import xbmcaddon as kodiaddon
import xbmcgui as kodigui
import xbmcvfs as kodivfs

import utils


class Ausis(object):

    def __init__(self, addon):
        self.addon = addon

    def log(self, msg, level=kodi.LOGDEBUG):
        log_enabled = (
            self.addon.getSetting('logging_enabled').lower() == True or not
            level == kodi.LOGDEBUG)
        if log_enabled:
            msg = ('%s: %s' % (
                self.addon.getAddonInfo('id'), msg)).encode('utf-8')
            kodi.log(msg=msg, level=level)

    def run(self, args):
        mode = args.get('mode') or 'main'

        if mode == 'scan':
            self.do_scan(args)
        elif mode == 'main':
            pass
        else:
            self.log('Unknown mode: %s' % mode, level=kodi.LOGERROR)

    def do_scan(self, args):
        directory = utils.decode_arg(
            self.addon.getSetting('audiobook_directory'))
        if not directory:
            kodigui.Dialog().ok(
                self.addon.getLocalizedString(30000),
                self.addon.getLocalizedString(30001),
            )
            return


def main():
    addon = kodiaddon.Addon(id='plugin.audio.ausis')
    args = parse_query(sys.argv[2][1:])
    Ausis(addon).run()
