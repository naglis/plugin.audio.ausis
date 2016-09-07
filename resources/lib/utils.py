# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
import os
import re
import urlparse


IMAGE_EXTENSIONS = ('jpg', 'jpeg', 'png')
AUDIO_EXTENSIONS = ('mp3', 'ogg')
COVER_FILENAMES = ('cover', 'folder', 'cover[\s_-]?art')
FANART_FILENAMES = ('fan[\s_-]?art',)


def decode_arg(arg):
    if isinstance(arg, str):
        arg = arg.decode('utf-8')
    return arg


def encode_arg(arg):
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    return arg


def decode_list(lst):
    return [decode_arg(item) for item in lst]


def encode_values(d):
    '''Given a dict d, returns a new dict with encoded keys and values.'''
    return dict([(encode_arg(k), encode_arg(v)) for k, v in d.iteritems()])


def parse_query(query, defaults=None):
    if defaults is None:
        defaults = {}

    d = defaults.copy()
    args = urlparse.parse_qs(query)
    for key, values in args.iteritems():
        if len(values) == 1:
            d[decode_arg(key)] = decode_arg(values[0])
        else:
            d[decode_arg(key)] = decode_list(values)
    return d


def make_regex_filename_matcher(filenames=None, extensions=None):
    if extensions is None:
        extensions = ('[a-z0-9]+',)
    if filenames is None:
        filenames = ('.+',)
    pattern = re.compile(r'(?i)^(%s)\.(%s)$' % (
        '|'.join(filenames), '|'.join(extensions)))

    def matcher(fn):
        return pattern.match(fn) is not None

    return matcher


def iscan_path(path, matcher):
    path_join = os.path.join
    for subdir, _, files in os.walk(path):
        for fn in files:
            if matcher(fn):
                yield path_join(subdir, fn)


audiofile_matcher = make_regex_filename_matcher(extensions=AUDIO_EXTENSIONS)
cover_matcher = make_regex_filename_matcher(
    filenames=COVER_FILENAMES, extensions=IMAGE_EXTENSIONS)
fanart_matcher = make_regex_filename_matcher(
    filenames=FANART_FILENAMES, extensions=IMAGE_EXTENSIONS)

ifind_audio = functools.partial(iscan_path, matcher=audiofile_matcher)
ifind_cover = functools.partial(iscan_path, matcher=cover_matcher)
ifind_fanart = functools.partial(iscan_path, matcher=fanart_matcher)


def format_duration(s):
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return '%d:%02d:%02d' % (h, m, s)
