# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import xbmc as kodi


class Service(object):

    def __init__(self):
        super(Service, self).__init__()
        self._monitor = kodi.Monitor()

    def run(self):
        while not self._monitor.abortRequested():
            if self._monitor.waitForAbort(1):
                break


class AudioBookPlayer(kodi.Player):

    def __init__(self, *args, **kwargs):
        super(AudioBookPlayer, self).__init__(*args, **kwargs)
        self.was_playing_audio = False
        self.current = None
        self.current_file = None
        kodi.log('Started ausis AudioBookPlayer', level=kodi.LOGINFO)

    def onPlayBackStarted(self):
        is_audio = self.isPlayingAudio()
        self.was_playing_audio = is_audio
        self.current = self.getMusicInfoTag() if is_audio else None
        self.current_file = self.getPlayingFile() if is_audio else None

    def onPlayBackPaused(self):
        current = self.getMusicInfoTag()
        kodi.log('Current: %s' % str(current), level=kodi.LOGINFO)


def main():
    player = AudioBookPlayer()
    Service().run()
