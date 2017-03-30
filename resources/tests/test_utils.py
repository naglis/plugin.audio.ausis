# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

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


@pytest.mark.parametrize('string, expected', [
    ('', None),
    ('foo', None),
    (None, None),
    ('1-2-3', None),
    ('2016-01-01', datetime.datetime(2016, 1, 1)),
    ('2016-01-01 12:04:05.123456',
        datetime.datetime(2016, 1, 1, 12, 4, 5, 123456)),
    ('12:04',
        datetime.datetime(1900, 1, 1, 12, 4)),
])
def test_parse_datetime_str(string, expected):
    assert utils.parse_datetime_str(string) == expected
