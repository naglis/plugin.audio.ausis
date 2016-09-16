# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sqlite3
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from lib import db

TEST_AUTHOR = 'Šatrijos Ragana'
TEST_TITLE = 'Viktutė'
TEST_PATH = '{TEST_AUTHOR:s} - {TEST_TITLE:s}'.format(**locals())
TEST_DURATION_1 = 3377
TEST_SIZE_1 = 40533561
TEST_FILES = [
    ['Lapkritis', '01 Viktutė.mp3', TEST_DURATION_1, TEST_SIZE_1],
]
TEST_NARRATOR = 'Dovilė Riškuvienė'
TEST_COVER_PATH = 'cover.jpg'
TEST_FANART_PATH = 'fanart.png'
TEST_AUDIOBOOK = [
    TEST_AUTHOR, TEST_TITLE, TEST_PATH, TEST_FILES, TEST_NARRATOR,
    TEST_COVER_PATH, TEST_FANART_PATH,
]


class TestDatabase(unittest.TestCase):

    def setUp(self):
        super(TestDatabase, self).setUp()
        self.db = db.AudioBookDB(':memory:')
        self.conn = self.db.get_conn()

    def tearDown(self):
        super(TestDatabase, self).tearDown()
        self.conn.close()

    def test_tables_are_created(self):
        with self.conn:
            for table in ('audiobooks', 'audiofiles', 'bookmarks'):
                try:
                    self.conn.execute('SELECT * FROM %s;' % table)
                except sqlite3.OperationalError:
                    self.fail('Table: %s was not created' % table)

    def test_add_audiobook(self):
        with self.conn as conn:
            cr = conn.cursor()
            db.add_audiobook(cr, *TEST_AUDIOBOOK)
            cr.execute('SELECT COUNT(1) FROM audiobooks;')
            result = cr.fetchone()
            self.assertEqual(result[0], 1)

    def test_get_all_audiobooks(self):
        with self.conn as conn:
            cr = conn.cursor()
            audiobook_id = db.add_audiobook(cr, *TEST_AUDIOBOOK)
            audiobooks = db.get_all_audiobooks(cr)
            self.assertEqual(
                len(audiobooks), 1, 'Incorrect number of audiobooks')
            self.assertEqual(audiobooks[0][b'id'], audiobook_id)

    def test_get_audiobook(self):
        with self.conn as conn:
            cr = conn.cursor()
            audiobook_id = db.add_audiobook(cr, *TEST_AUDIOBOOK)
            audiobook, items = db.get_audiobook(cr, audiobook_id)
            self.assertEqual(audiobook[b'id'], audiobook_id)
            self.assertEqual(
                len(items), 1, 'Incorrect number of audiofiles')

    def test_get_audiobook_by_path(self):
        with self.conn as conn:
            cr = conn.cursor()
            audiobook_id = db.add_audiobook(cr, *TEST_AUDIOBOOK)
            self.assertEqual(
                audiobook_id, db.get_audiobook_by_path(cr, TEST_PATH))
            self.assertFalse(
                db.get_audiobook_by_path(cr, 'NON_EXISTING_PATH'),
                msg='Audiobook at non-existing path was found',
            )

    def test_get_cover(self):
        with self.conn as conn:
            cr = conn.cursor()
            audiobook_id = db.add_audiobook(cr, *TEST_AUDIOBOOK)
            self.assertEqual(db.get_cover(cr, audiobook_id), TEST_COVER_PATH)

    def test_set_cover(self):
        with self.conn as conn:
            cr = conn.cursor()
            new_cover_path = 'folder.jpg'
            audiobook_id = db.add_audiobook(cr, *TEST_AUDIOBOOK)
            db.set_cover(cr, audiobook_id, new_cover_path)
            self.assertEqual(db.get_cover(cr, audiobook_id), new_cover_path)

    def test_get_fanart(self):
        with self.conn as conn:
            cr = conn.cursor()
            audiobook_id = db.add_audiobook(cr, *TEST_AUDIOBOOK)
            self.assertEqual(db.get_fanart(cr, audiobook_id), TEST_FANART_PATH)

    def test_set_fanart(self):
        with self.conn as conn:
            cr = conn.cursor()
            new_fanart_path = 'fan_art.jpg'
            audiobook_id = db.add_audiobook(cr, *TEST_AUDIOBOOK)
            db.set_fanart(cr, audiobook_id, new_fanart_path)
            self.assertEqual(db.get_fanart(cr, audiobook_id), new_fanart_path)
