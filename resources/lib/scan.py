# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import collections

import utils

path_join = os.path.join
norm_path = os.path.normpath


class SkipAudiobookDir(Exception):
    '''Raised when a directory should be skipped (eg. contains ignore file)'''


def scan_subdir(root, subdir):
    m = {'audio': [], 'cover': [], 'fanart': []}
    audiobook_dir = path_join(root, subdir)
    level = 0
    for root2, _, files in os.walk(audiobook_dir):
        rel_dir = os.path.relpath(root2, audiobook_dir)
        for fn in files:
            rel_fn = norm_path(path_join(rel_dir, fn))
            if level == 0:
                if utils.ignore_matcher(fn):
                    raise SkipAudiobookDir('Found ignore file')
                if utils.cover_matcher(fn):
                    m['cover'].append(rel_fn)
                if utils.fanart_matcher(fn):
                    m['fanart'].append(rel_fn)
            if utils.audiofile_matcher(fn):
                m['audio'].append(rel_fn)
        level += 1
    return m


def scan(path, progress_cb=None):
    for root, subdirs, _ in os.walk(path):
        total = float(len(subdirs))
        for idx, subdir in enumerate(subdirs, start=1):
            if progress_cb:
                progress_cb(int(100 * idx / total))
            try:
                m = scan_subdir(root, subdir)
            except SkipAudiobookDir as e:
                pass
            else:
                yield subdir, m
        break


def cb(p):
    print(p)


if __name__ == '__main__':

    for i in scan('/home/naglis/downloads/audiobooks/', cb):
        pass
