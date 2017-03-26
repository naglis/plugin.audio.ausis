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


def bookmark_factory(cursor, row):
    return Bookmark(*row)


class AusisDatabase(object):

    SCHEMA = SQL_SCHEMA

    def __init__(self, db_path):
        self._db_path = db_path
        self._conn = None
        self._cr = None

    @property
    def cr(self):
        return self._cr

    def initialize(self):
        self._cr.executescript(self.SCHEMA)

    def _connect(self):
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = bookmark_factory
        self._cr = self._conn.cursor()

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

    def add_bookmark(self, name, song_id, album_id, position):
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
        bookmark = self.cr.fetchone()

        now = int(time.time())
        if bookmark:
            q = '''
            UPDATE
                bookmark
            SET
                position = :position,
                date_added = :date_added
            WHERE
                id = :id
            ;'''
            self.cr.execute(q, {
                'id': bookmark.id,
                'position': position,
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

    def get_all_bookmarks(self):
        self.cr.execute('SELECT * FROM bookmark;')
        return self.cr.fetchall()

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
        result = self.cr.fetchone()
        return result if result else None

    def get_album_bookmarks(self, album_id):
        query = '''
        SELECT
            *
        FROM
            bookmark
        WHERE
            album_id = :album_id
        ;'''
        self.cr.execute(query, locals())
        return self.cr.fetchall()
