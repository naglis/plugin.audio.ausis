# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from lib import db as database, utils

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


class DummyDatabase(database.Database):
    SCHEMA = 'CREATE TABLE IF NOT EXISTS test (value varchar);'

    def put_value(self, value):
        self.cr.execute(
            'INSERT INTO test (value) VALUES (:value);', locals())

    def has_value(self, value):
        self.cr.execute(
            'SELECT COUNT(1) FROM test WHERE value = :value', locals())
        return bool(utils.first_of(self.cr.fetchone()))


class TestDatabase(unittest.TestCase):

    def test_initialize_initializes_schema(self):
        db = DummyDatabase(':memory:')
        db._connect()
        db.initialize()
        db.cr.execute('''
            SELECT
                COUNT(1)
            FROM
                sqlite_master
            WHERE
                type='table'
            AND
                name='test'
        ;''')
        self.assertEqual(utils.first_of(db.cr.fetchone()), 1)

    def test_exception_inside_with_statement_rollbacks_changes(self):
        with tempfile.NamedTemporaryFile() as tmp:
            dummy_db = DummyDatabase(tmp.name)
            try:
                with dummy_db as db:
                    db.put_value('Hello')
                    1 / 0
            except ZeroDivisionError:
                pass

            with dummy_db as db:
                self.assertFalse(db.has_value('Hello'))


class TestAusisDatabase(unittest.TestCase):

    def setUp(self):
        super(TestAusisDatabase, self).setUp()
        self.db = database.AusisDatabase(':memory:')

    def test_tables_are_created(self):
        with self.db as db:
            for table in ('audiobooks', 'audiofiles', 'bookmarks'):
                try:
                    db.cr.execute('SELECT * FROM %s;' % table)
                except sqlite3.OperationalError:
                    self.fail('Table: %s was not created' % table)

    def test_add_audiobook(self):
        with self.db as db:
            db.add_audiobook(*TEST_AUDIOBOOK)
            db.cr.execute('SELECT COUNT(1) FROM audiobooks;')
            result = db.cr.fetchone()
            self.assertEqual(result[0], 1)

    def test_get_all_audiobooks(self):
        with self.db as db:
            audiobook_id = db.add_audiobook(*TEST_AUDIOBOOK)
            audiobooks = db.get_all_audiobooks()
            self.assertEqual(
                len(audiobooks), 1, 'Incorrect number of audiobooks')
            self.assertEqual(audiobooks[0][b'id'], audiobook_id)

    def test_get_audiobook(self):
        with self.db as db:
            audiobook_id = db.add_audiobook(*TEST_AUDIOBOOK)
            audiobook, items = db.get_audiobook(audiobook_id)
            self.assertEqual(audiobook[b'id'], audiobook_id)
            self.assertEqual(
                len(items), 1, 'Incorrect number of audiofiles')

    def test_get_audiobook_by_path(self):
        with self.db as db:
            audiobook_id = db.add_audiobook(*TEST_AUDIOBOOK)
            self.assertEqual(
                audiobook_id, db.get_audiobook_by_path(TEST_PATH))
            self.assertFalse(
                db.get_audiobook_by_path('NON_EXISTING_PATH'),
                msg='Audiobook at non-existing path was found',
            )

    def test_get_cover(self):
        with self.db as db:
            audiobook_id = db.add_audiobook(*TEST_AUDIOBOOK)
            self.assertEqual(db.get_cover(audiobook_id), TEST_COVER_PATH)

    def test_set_cover(self):
        with self.db as db:
            new_cover_path = 'folder.jpg'
            audiobook_id = db.add_audiobook(*TEST_AUDIOBOOK)
            db.set_cover(audiobook_id, new_cover_path)
            self.assertEqual(db.get_cover(audiobook_id), new_cover_path)

    def test_get_fanart(self):
        with self.db as db:
            audiobook_id = db.add_audiobook(*TEST_AUDIOBOOK)
            self.assertEqual(db.get_fanart(audiobook_id), TEST_FANART_PATH)

    def test_set_fanart(self):
        with self.db as db:
            new_fanart_path = 'fan_art.jpg'
            audiobook_id = db.add_audiobook(*TEST_AUDIOBOOK)
            db.set_fanart(audiobook_id, new_fanart_path)
            self.assertEqual(db.get_fanart(audiobook_id), new_fanart_path)
