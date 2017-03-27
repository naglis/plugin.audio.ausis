# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections
import operator
import sqlite3
import time

DB_FILE_NAME = 'ausis.sqlite'

BOOKMARK_FIELDS = [
    'id',
    'name',
    'song_id',
    'album_id',
    'position',
    'date_added',
]
Bookmark = collections.namedtuple('Bookmark', BOOKMARK_FIELDS)

duration_getter = operator.attrgetter('duration')

SQL_SCHEMA = '''
CREATE TABLE IF NOT EXISTS bookmark (
    id INTEGER NOT NULL,
    name VARCHAR(255),
    song_id INTEGER NOT NULL,
    album_id INTEGER NOT NULL,
    position REAL NOT NULL,
    date_added INTEGER DEFAULT 0,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS bookmark_name_idx ON bookmark(name);
CREATE INDEX IF NOT EXISTS bookmark_song_idx ON bookmark(song_id);
CREATE INDEX IF NOT EXISTS bookmark_album_idx ON bookmark(album_id);
'''


def wrap_bookmark(results):
    if results is None:
        return
    if isinstance(results, tuple):
        return Bookmark(*results)
    return [Bookmark(*r) for r in results]


class Database(object):

    SCHEMA = None

    def __init__(self, db_path):
        self._db_path = db_path
        self._conn = None
        self._cr = None

    def __enter__(self):
        self._connect()
        self.initialize()
        return self

    def __exit__(self, exc_class, exc, traceback):
        if any((exc_class, exc)):
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()

    def _connect(self):
        self._conn = sqlite3.connect(self._db_path)
        self._cr = self._conn.cursor()

    @property
    def cr(self):
        return self._cr

    def initialize(self):
        self._cr.executescript(self.SCHEMA)


class AusisDatabase(Database):

    SCHEMA = SQL_SCHEMA

    def add_bookmark(self, name, song_id, album_id, position):
        now = int(time.time())
        if name == 'started':
            bookmark = None
            q = '''
            SELECT
                *
            FROM
                bookmark
            WHERE
                name = :name
            AND
                song_id = :song_id
            AND
                album_id = :album_id
            ;'''
            self.cr.execute(q, locals())
            bookmark = wrap_bookmark(self.cr.fetchone())

            if bookmark:
                q = '''
                UPDATE
                    bookmark
                SET
                    date_added = :date_added
                WHERE
                    id = :id
                ;'''
                self.cr.execute(q, {
                    'id': bookmark.id,
                    'date_added': now,
                })
                return bookmark.id

        query = '''
        INSERT INTO bookmark (
            name,
            song_id,
            album_id,
            position,
            date_added
        ) VALUES (
            :name,
            :song_id,
            :album_id,
            :position,
            :now
        );'''
        self.cr.execute(query, locals())
        return self.cr.lastrowid

    def get_albums(self):
        query = '''
        SELECT
            *
        FROM
            bookmark
        GROUP BY
            album_id
        ORDER BY
            date_added DESC
        ;'''
        return wrap_bookmark(self.cr.execute(query).fetchall())

    def get_all_bookmarks(self):
        return wrap_bookmark(
            self.cr.execute('SELECT * FROM bookmark;').fetchall())

    def get_bookmark(self, bookmark_id):
        query = '''
        SELECT
            *
        FROM
            bookmark
        WHERE
            id = :bookmark_id
        ;'''
        self.cr.execute(query, locals())
        result = wrap_bookmark(self.cr.fetchone())
        return result if result else None

    def get_album_bookmarks(self, album_id):
        query = '''
        SELECT
            *
        FROM
            bookmark
        WHERE
            album_id = :album_id
        ORDER BY
            date_added DESC
        ;'''
        return wrap_bookmark(self.cr.execute(query, locals()).fetchall())
