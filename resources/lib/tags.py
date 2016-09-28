# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections

import mutagen

import utils


Tags = collections.namedtuple(
    'Tags', ['artist', 'album', 'title', 'narrator', 'duration'])


def single_item(tags):
    if isinstance(tags, list):
        return utils.first_of(tags)
    else:
        return tags


def id3_getter(tag, tags):
    v = tags.get(tag)
    if v:
        return single_item(v.text)


def get_tags(file_path):
    tags = mutagen.File(file_path)
    duration = int(tags.info.length)
    ftype = type(tags.info)
    if ftype == mutagen.oggvorbis.OggVorbisInfo:
        artist = single_item(tags.get('artist'))
        album = single_item(tags.get('album'))
        title = single_item(tags.get('title'))
    elif ftype == mutagen.mp3.MPEGInfo:
        artist = id3_getter('TPE1', tags)
        album = id3_getter('TALB', tags)
        title = id3_getter('TIT2', tags)
    elif ftype == mutagen.mp4.MP4Info:
        artist = single_item(tags.get(b'\xa9ART'))
        album = single_item(tags.get(b'\xa9alb'))
        title = single_item(tags.get(b'\xa9nam'))
    else:
        raise ValueError('Unknown file type')
    return Tags(
        artist=artist,
        album=album,
        title=title,
        narrator=None,
        duration=duration,
    )
