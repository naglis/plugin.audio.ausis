# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import datetime
import json
import operator
import urlparse


SQLITE_DATETIME_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d',
    '%H:%M:%S',
    '%H:%M:%S.%f',
    '%H:%M',
)

first_of = operator.itemgetter(0)


def decode_arg(arg):
    if isinstance(arg, str):
        arg = arg.decode('utf-8')
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


# TODO(naglis): maybe move this to DB model.
def latest_bookmark(bookmarks):
    return first_of(
        sorted(bookmarks, key=operator.attrgetter('date_added'), reverse=True)
    )


# TODO(naglis): maybe move this to DB model.
def furthest_bookmark(bookmarks):
    return first_of(
        sorted(
            bookmarks,
            key=operator.attrgetter('audiofile.sequence', 'position'),
            reverse=True,
        )
    )


def parse_datetime_str(s, formats=SQLITE_DATETIME_FORMATS):
    for fmt in formats:
        try:
            return datetime.datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            pass
