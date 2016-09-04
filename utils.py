# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
import os
import re
import urlparse


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


def iglob_ext(path, filenames=None, extensions=None):
    if extensions is None:
        extensions = ('[a-z0-9]+',)
    if filenames is None:
        filenames = ('.+',)
    pattern = re.compile(r'(?i)^(%s)\.(%s)$' % (
        '|'.join(filenames), '|'.join(extensions)))
    for subdir, _, files in os.walk(path):
        for fn in files:
            if pattern.match(fn):
                yield os.path.join(subdir, fn)


iscan = functools.partial(iglob_ext, extensions=('mp3', 'ogg', 'flac', 'wma'))
ifind_cover = functools.partial(
    iglob_ext, filenames=('cover', 'folder'), extensions=('jpg', 'png'))
ifind_fanart = functools.partial(
    iglob_ext, filenames=('fanart', 'fan_art'), extensions=('jpg', 'png'))


def format_duration(s):
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return '%d:%02d:%02d' % (h, m, s)
