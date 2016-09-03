# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re
import urlparse


SUITABLE_FILE = re.compile(r'(?i)^.*\.(mp3|ogg|flac|wma)$')


def decode_arg(arg):
    if isinstance(arg, str):
        arg = arg.decode('utf-8')
    return arg


def decode_list(lst):
    return [decode_arg(item) for item in lst]


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


def scan(path):
    for subdir, dirs, files in os.walk(path):
        for fn in files:
            if SUITABLE_FILE.match(fn):
                yield os.path.join(path, subdir, fn)
