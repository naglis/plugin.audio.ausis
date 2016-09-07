from __future__ import unicode_literals

import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from lib import utils


class TestUtils(unittest.TestCase):

    def test_format_duration(self):
        test_cases = [
            (1, '0:00:01'),
            (61, '0:01:01'),
            (3601, '1:00:01'),
            (3661, '1:01:01'),
        ]
        for s, expected in test_cases:
            actual = utils.format_duration(s)
            self.assertEqual(actual, expected)

    def test_audiofile_matcher(self):
        test_cases = [
            ('test.ogg', True),
            ('test.Ogg', True),
            ('test.OGG', True),
            ('test.wav.OGG', True),
            ('test.ogg.wav', False),
            ('test.mp3', True),
            ('test.wav', False),
        ]
        for fn, expected in test_cases:
            actual = utils.audiofile_matcher(fn)
            self.assertEqual(
                actual, expected, 'Matching audiofile: %s incorrectly' % fn)

    def test_coverfile_matcher(self):
        test_cases = [
            ('folder.jpg', True),
            ('folder.png', True),
            ('cover.jpg', True),
            ('cover.png', True),
            ('cover.jpeg', True),
            ('art.jpg', False),
            ('cover.gif', False),
            ('coverart.jpg', True),
            ('cover_art.jpg', True),
            ('cover art.jpg', True),
            ('cover-art.jpg', True),
        ]
        for fn, expected in test_cases:
            actual = utils.cover_matcher(fn)
            self.assertEqual(
                actual, expected, 'Matching cover: %s incorrectly' % fn)

    def test_fanart_matcher(self):
        test_cases = [
            ('fanart.jpg', True),
            ('FANART.png', True),
            ('fan_art.jpg', True),
            ('fan art.png', True),
            ('fan-art.jpeg', True),
            ('fanart.gif', False),
        ]
        for fn, expected in test_cases:
            actual = utils.fanart_matcher(fn)
            self.assertEqual(
                actual, expected, 'Matching fanart: %s incorrectly' % fn)
