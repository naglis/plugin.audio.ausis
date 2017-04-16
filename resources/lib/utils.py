# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import json
import operator
import os
import urlparse


first_of = operator.itemgetter(0)


def decode_arg(arg, encoding='utf-8'):
    if isinstance(arg, str):
        arg = arg.decode(encoding)
    return arg


def encode_arg(arg):
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    return arg


def encode_values(d):
    '''Given a dict d, returns a new dict with encoded keys and values.'''
    return {encode_arg(k): encode_arg(v) for k, v in d.items()}


def dump_data(data):
    return base64.b64encode(json.dumps(data)) if data else ''


def load_data(s):
    return json.loads(base64.b64decode(s)) if s else {}


def parse_query(query, defaults=None):
    if defaults is None:
        defaults = {}

    d = defaults.copy()
    args = urlparse.parse_qs(query)
    for key, values in args.items():
        if len(values) == 1:
            d[decode_arg(key)] = decode_arg(first_of(values))
        else:
            d[decode_arg(key)] = map(decode_arg, values)
    return d


def format_duration(s):
    s = int(s)
    sign = '-' if s < 0 else ''
    s = abs(s)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return '%s%d:%02d:%02d' % (sign, h, m, s)


def in_directory(filename, directory):
    '''
    Check if a file is somewhere inside a directory.

    Based on http://stackoverflow.com/q/3812849/
    '''
    filename, directory = map(os.path.realpath, [filename, directory])
    directory = os.path.join(directory, '')
    return os.path.commonprefix([filename, directory]) == directory
