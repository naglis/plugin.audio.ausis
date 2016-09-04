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


def iglob_ext(path, extensions=None):
    if not extensions:
        raise ValueError('You must specify at least one extension!')
    pattern = re.compile(r'(?i)^.*\.(%s)$' % '|'.join(extensions))
    for subdir, _, files in os.walk(path):
        for fn in files:
            if pattern.match(fn):
                yield os.path.join(subdir, fn)


iscan = functools.partial(iglob_ext, extensions=('mp3', 'ogg', 'flac', 'wma'))


def find_cover(path):
    pattern = re.compile(r'(?i)^(folder|cover)')
    for fn in iglob_ext(path, extensions=('png', 'jpg')):
        if pattern.match(os.path.basename(fn)):
            yield fn
