# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from lib import utils


@pytest.mark.parametrize('input, output', [
    (1, '0:00:01'),
    (61, '0:01:01'),
    (3601, '1:00:01'),
    (3661, '1:01:01'),
    (-1, '-0:00:01'),
    (-61, '-0:01:01'),
    (-0.00001, '0:00:00'),
])
def test_format_duration(input, output):
    assert utils.format_duration(input) == output


@pytest.mark.parametrize('query, args', [
    ('a=1&b=3&c=2&d=', {'a': '1', 'b': '3', 'c': '2'}),
    ('a=1&b=3&c=2&b=4', {'a': '1', 'b': ['3', '4'], 'c': '2'}),
])
def test_parse_query_single_value(query, args):
    assert utils.parse_query(query) == args


@pytest.mark.parametrize('input, expected', [
    ({u'a': u'b'}, {'a': 'b'}),
    ({'a': u'b'}, {'a': 'b'}),
    ({u'a': 'b'}, {'a': 'b'}),
    ({'a': 'b'}, {'a': 'b'}),
])
def test_encode_values(input, expected):
    assert utils.encode_values(input) == expected


@pytest.mark.parametrize('filename, directory, expected', [
    ('/home/foo/ab/test/test.mp3', '/home/foo/ab', True),
    ('/home/foo/abc/test/test.mp3', '/home/foo/ab', False),
    ('zip:///home/foo/ab/test/test.zip', '/home/foo/ab', True),
])
def test_in_directory(filename, directory, expected):
    assert utils.in_directory(filename, directory) == expected
