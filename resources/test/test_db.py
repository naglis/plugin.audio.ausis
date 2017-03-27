# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import tempfile
import unittest

from lib import db as database, utils

BOOKMARK_DATA = [
    database.Bookmark(None, 'started', 1, 2, 3.45, None),
    database.Bookmark(None, 'paused', 2, 2, 6.78, None),
    database.Bookmark(None, 'started', 3, 4, 7.89, None),
]


def table_exists(cr, table):
    '''Checks if :param:`table` exists in the sqlite database.'''
    cr.execute('''
    SELECT
        COUNT(1)
    FROM
        sqlite_master
    WHERE
        type = 'table'
    AND
        name = :table
    ;''', locals())
    return bool(utils.first_of(cr.fetchone()))


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
        self.assertTrue(table_exists(db.cr, 'test'))

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
            for table in ('bookmark', ):
                self.assertTrue(
                    table_exists(db.cr, table),
                    msg='Table: %s was not created' % table,
                )

    def test_add_bookmark(self):
        data = BOOKMARK_DATA[0]
        with self.db as db:
            bookmark_id = db.add_bookmark(*data[1:-1])
            bookmark = database.wrap_bookmark(db.cr.execute('''
            SELECT
                *
            FROM
                bookmark
            WHERE
                id = :bookmark_id
            ;''', locals()).fetchone())
            self.assertEqual(data.song_id, bookmark.song_id)
            self.assertEqual(data.album_id, bookmark.album_id)
            self.assertEqual(data.position, bookmark.position)

    def test_add_bookmark_update_same_id(self):
        data = BOOKMARK_DATA[0]
        with self.db as db:
            bookmark_id1 = db.add_bookmark(*data[1:-1])
            bookmark_id2 = db.add_bookmark(*data[1:-1])
            self.assertEqual(bookmark_id1, bookmark_id2)

    def test_get_albums(self):
        with self.db as db:
            for bookmark in BOOKMARK_DATA:
                db.add_bookmark(*bookmark[1:-1])
            album_bookmarks = db.get_albums()
            self.assertEqual(len(album_bookmarks), 2)

    def test_get_all_bookmarks(self):
        with self.db as db:
            for bookmark in BOOKMARK_DATA:
                db.add_bookmark(*bookmark[1:-1])
            album_bookmarks = db.get_all_bookmarks()
            self.assertEqual(len(album_bookmarks), 3)

    def test_get_bookmark(self):
        data = BOOKMARK_DATA[0]
        with self.db as db:
            bookmark_id = db.add_bookmark(*data[1:-1])
            self.assertTrue(db.get_bookmark(bookmark_id))

    def test_get_album_bookmarks(self):
        with self.db as db:
            for bookmark in BOOKMARK_DATA:
                db.add_bookmark(*bookmark[1:-1])
            album_bookmarks = db.get_album_bookmarks(2)
            self.assertEqual(len(album_bookmarks), 2)
