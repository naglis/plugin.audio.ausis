# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import json
import operator
import re
import urlparse


IMAGE_EXTENSIONS = (r'jpg', r'jpeg', r'png')
AUDIO_EXTENSIONS = (r'mp3', r'ogg')
COVER_FILENAMES = (r'cover', r'folder', r'cover[\s_-]?art')
FANART_FILENAMES = (r'fan[\s_-]?art',)
IGNORE_FILENAME = b'.ausis_ignore'

first_of = operator.itemgetter(0)


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


def dump_data(data):
    return base64.b64encode(json.dumps(data)) if data else ''


def load_data(s):
    return json.loads(base64.b64decode(s)) if s else {}


def parse_query(query, defaults=None):
    if defaults is None:
        defaults = {}

    d = defaults.copy()
    args = urlparse.parse_qs(query)
    for key, values in args.iteritems():
        if len(values) == 1:
            d[decode_arg(key)] = decode_arg(first_of(values))
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


audiofile_matcher = make_regex_filename_matcher(extensions=AUDIO_EXTENSIONS)
cover_matcher = make_regex_filename_matcher(
    filenames=COVER_FILENAMES, extensions=IMAGE_EXTENSIONS)
fanart_matcher = make_regex_filename_matcher(
    filenames=FANART_FILENAMES, extensions=IMAGE_EXTENSIONS)


def ignore_matcher(fn):
    return fn == IGNORE_FILENAME


def format_duration(s):
    sign = '-' if s < 0 else ''
    s = abs(s)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return '%s%d:%02d:%02d' % (sign, h, m, s)
