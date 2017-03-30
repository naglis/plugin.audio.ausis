# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import tempfile

import pytest

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


@pytest.fixture
def one_bookmark():
    return BOOKMARK_DATA[0]


@pytest.fixture
def one_bookmark_data():
    return BOOKMARK_DATA[0][1:-1]


@pytest.fixture
def bookmarks_data():
    return [b[1:-1] for b in BOOKMARK_DATA]


@pytest.fixture
def mem_db():
    return DummyDatabase(':memory:')


@pytest.fixture
def ausis_mem_db():
    return database.AusisDatabase(':memory:')


@pytest.yield_fixture
def temp_db():
    tmp_file = tempfile.NamedTemporaryFile()
    yield DummyDatabase(tmp_file.name)
    tmp_file.close()


def test_initialize_initializes_schema(mem_db):
    mem_db._connect()
    mem_db.initialize()
    assert table_exists(mem_db.cr, 'test')


def test_exception_inside_with_statement_rollbacks_changes(temp_db):
    try:
        with temp_db as db:
            db.put_value('Hello')
            1 / 0
    except ZeroDivisionError:
        pass

    with temp_db as db:
        assert not db.has_value('Hello')


@pytest.mark.parametrize('db, table', [
    (ausis_mem_db(), 'bookmark')
])
def test_bookmark_table_is_created(db, table):
    with db:
        assert table_exists(db.cr, table), 'Table: %s was not created' % table


def test_add_bookmark(ausis_mem_db, one_bookmark):
    data = one_bookmark[1:-1]
    with ausis_mem_db as db:
        bookmark_id = db.add_bookmark(*data)
        new_bookmark = database.wrap_bookmark(db.cr.execute(
            'SELECT * FROM bookmark WHERE id = :bookmark_id;', locals()
            ).fetchone())

    assert one_bookmark.song_id == new_bookmark.song_id
    assert one_bookmark.album_id == new_bookmark.album_id
    assert one_bookmark.position == new_bookmark.position


def test_add_bookmark_update_same_id(ausis_mem_db, one_bookmark_data):
    with ausis_mem_db as db:
        bookmark_id1 = db.add_bookmark(*one_bookmark_data)
        bookmark_id2 = db.add_bookmark(*one_bookmark_data)
        assert bookmark_id1 == bookmark_id2


def test_get_albums(ausis_mem_db, bookmarks_data):
    with ausis_mem_db as db:
        for data in bookmarks_data:
            db.add_bookmark(*data)
        assert len(db.get_albums()) == 2


def test_get_all_bookmarks(ausis_mem_db, bookmarks_data):
    with ausis_mem_db as db:
        for data in bookmarks_data:
            db.add_bookmark(*data)
        assert len(db.get_all_bookmarks()) == 3


def test_get_bookmark(ausis_mem_db, one_bookmark_data):
    with ausis_mem_db as db:
        bookmark_id = db.add_bookmark(*one_bookmark_data)
        assert db.get_bookmark(bookmark_id).id == bookmark_id


def test_get_album_bookmarks(ausis_mem_db, bookmarks_data):
    with ausis_mem_db as db:
        for data in bookmarks_data:
            db.add_bookmark(*data)
        assert len(db.get_album_bookmarks(2)) == 2


def test_remove_album_bookmarks(ausis_mem_db, bookmarks_data):
    remove_album_id, other_album_id = 2, 4
    with ausis_mem_db as db:
        for data in bookmarks_data:
            db.add_bookmark(*data)
        removed = db.remove_album_bookmarks(remove_album_id)
        assert removed
        assert not db.get_album_bookmarks(remove_album_id)
        assert len(db.get_album_bookmarks(other_album_id)) == 1
