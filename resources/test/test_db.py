# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
import unittest

from lib import utils
from lib.db import (
    Audiobook,
    Audiofile,
    Bookmark,
    database,
)

TEST_AUTHOR = 'Šatrijos Ragana'
TEST_TITLE = 'Viktutė'
TEST_PATH = '{TEST_AUTHOR:s} - {TEST_TITLE:s}'.format(**locals())
DURATION_1H = 60 * 60
DURATION_30M = 30 * 60
SIZE_40M = 40 * 1024 * 1024
TEST_FILES = {
    1: ('Lapkritis', '01 Viktutė.mp3', DURATION_1H, SIZE_40M),
    2: ('Gruodis', '02 Viktutė.mp3', DURATION_30M, SIZE_40M),
}
TEST_NARRATOR = 'Dovilė Riškuvienė'
TEST_COVER_PATH = 'cover.jpg'
TEST_FANART_PATH = 'fanart.png'
TEST_AUDIOBOOK = [
    TEST_AUTHOR, TEST_TITLE, TEST_PATH, TEST_FILES, TEST_NARRATOR,
    TEST_COVER_PATH, TEST_FANART_PATH,
]
POSITION_42 = 42
POSITION_314 = 314
DATETIME_2016_1_1 = datetime.datetime(2016, 1, 1, 12)
DATETIME_2016_1_2 = datetime.datetime(2016, 1, 2, 12)


def table_exists(table):
    '''Checks if :param:`table` exists in the sqlite database.'''
    result = database.execute_sql('''
    SELECT
        COUNT(1)
    FROM
        sqlite_master
    WHERE
        type = 'table'
    AND
        name = :table
    ;''', locals())
    return bool(utils.first_of(result.fetchone()))


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        super(DatabaseTestCase, self).setUp()
        database.init(':memory:')
        database.connect()
        database.create_tables([Audiobook, Audiofile, Bookmark], safe=True)


class TestDatabase(DatabaseTestCase):

    def test_init_initializes_schema(self):
        self.assertTrue(table_exists('audiobook'))
        self.assertTrue(table_exists('audiofile'))
        self.assertTrue(table_exists('bookmark'))


class TestAudiobook(DatabaseTestCase):

    def setUp(self):
        super(TestAudiobook, self).setUp()
        self.audiobook = Audiobook.create(
            author=TEST_AUTHOR,
            title=TEST_TITLE,
            path=TEST_PATH,
            cover=TEST_COVER_PATH,
            fanart=TEST_FANART_PATH,
        )
        self.audiofiles = {}
        for idx, (title, path, duration, size) in TEST_FILES.iteritems():
            audiofile = Audiofile.create(
                audiobook=self.audiobook,
                title=title,
                sequence=idx,
                file_path=path,
                duration=duration,
                size=size,
            )
            self.audiofiles[idx] = audiofile

        self.bookmarks = []
        bookmarks = [
            (POSITION_42, DATETIME_2016_1_1),
            (POSITION_314, DATETIME_2016_1_2),
        ]
        audiofile = utils.first_of(self.audiofiles.values())
        for pos, date_added in bookmarks:
            self.bookmarks.append(
                Bookmark.create(
                    audiofile=audiofile,
                    position=pos,
                    date_added=date_added,
                )
            )

    def test_from_path_with_correct_path_returns_audiobook(self):
        audiobook = Audiobook.from_path(TEST_PATH)
        self.assertEqual(audiobook, self.audiobook)

    def test_from_path_with_some_incorrect_path_returns_None(self):
        audiobook = Audiobook.from_path(TEST_PATH + 'blah')
        self.assertFalse(audiobook)

    def test_last_played_with_two_bookmarks_returns_latest(self):
        last_played = self.audiobook.last_played
        self.assertEqual(last_played, DATETIME_2016_1_2)

    def test_audiobook_duration_calculation(self):
        self.assertEqual(self.audiobook.duration, DURATION_1H + DURATION_30M)

    def test_audiobook_cover_path_calculation(self):
        self.assertEqual(
            self.audiobook.cover_path,
            os.path.join(TEST_PATH, TEST_COVER_PATH),
        )

    def test_audiobook_cover_fanart_calculation(self):
        self.assertEqual(
            self.audiobook.fanart_path,
            os.path.join(TEST_PATH, TEST_FANART_PATH),
        )

    def test_remove_audiobook_removes_its_bookmarks(self):
        audiofile_id = utils.first_of(self.audiofiles.values()).id
        self.audiobook.delete_instance()
        results = Bookmark.select().where(audiofile_id == audiofile_id)
        self.assertFalse(results)
