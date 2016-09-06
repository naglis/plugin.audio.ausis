# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import sqlite3


DB_FILE_NAME = 'ausis.sqlite'


class AudioBookDB(object):

    def __init__(self, db_path):
        self._db_path = db_path

    @classmethod
    def get_db(cls, db_path):
        db = cls(db_path)
        db.init_db()
        return db

    def get_conn(self):
        conn = sqlite3.connect(
            self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys;')
        return conn

    def init_db(self):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                cr = conn.cursor()
                cr.executescript('''
CREATE TABLE IF NOT EXISTS audiobooks (
    id INTEGER NOT NULL,
    title VARCHAR(256) NOT NULL,
    author VARCHAR(256) NOT NULL,
    narrator VARCHAR(256),
    path VARCHAR NOT NULL,
    cover_path VARCHAR,
    fanart_path VARCHAR,
    summary TEXT,
    date_added TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (id)
);
CREATE TABLE IF NOT EXISTS audiofiles (
    id INTEGER NOT NULL,
    audiobook_id INTEGER,
    title VARCHAR,
    file_path VARCHAR NOT NULL, -- Relative to audiobook.path
    duration INTEGER,
    sequence INTEGER NOT NULL,
    size INTEGER DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE (id),
    FOREIGN KEY(audiobook_id) REFERENCES audiobooks (id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER NOT NULL,
    audiofile_id INTEGER,
    audiobook_id INTEGER,
    position INTEGER,
    PRIMARY KEY (id),
    UNIQUE (id),
    FOREIGN KEY(audiofile_id) REFERENCES audiofiles (id) ON DELETE CASCADE,
    FOREIGN KEY(audiobook_id) REFERENCES audiobooks (id) ON DELETE CASCADE
);''')

    def add_audiobook(self, author, title, path, files, narrator=None,
                      cover_path=None, fanart_path=None, summary=None):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                cr = conn.cursor()
                query = '''
INSERT INTO audiobooks (
    author,
    title,
    narrator,
    path,
    cover_path,
    fanart_path,
    summary,
    date_added
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, DATETIME('now')
);'''
                data = (author, title, narrator, path, cover_path, fanart_path,
                        summary)
                cr.execute(query, data)
                audiobook_id = cr.lastrowid

                audiofile_ids = []
                for sequence, item in enumerate(files, start=1):
                    title, file_path, duration, size = item
                    query = '''
INSERT INTO audiofiles (
    audiobook_id,
    title,
    file_path,
    duration,
    sequence,
    size
) VALUES (
    ?, ?, ?, ?, ?, ?
);'''
                    data = (
                        audiobook_id, title, file_path, duration, sequence,
                        size,
                    )
                    cr.execute(query, data)
                    audiofile_ids.append(cr.lastrowid)

                return {audiobook_id: audiofile_ids}

    def audiobook_exists(self, subdir):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                cr = conn.cursor()
                query = '''
SELECT
    *
FROM
    audiobooks
WHERE
    path = ?
LIMIT
    1;'''
                cr.execute(query, (subdir,))
                res = cr.fetchone()
                return bool(res)

    def get_all_audiobooks(self):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                query = '''
SELECT
    *,
    a.date_added as "date_added [timestamp]",
    SUM(f.duration) AS duration
FROM
    audiobooks AS a
JOIN
    audiofiles AS f
ON
    a.id = f.audiobook_id
GROUP BY
    f.audiobook_id
ORDER BY
    a.date_added;
'''
                cr = conn.cursor()
                cr.execute(query)
                return cr.fetchall()

    def get_audiobook(self, audiobook_id):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                query = 'SELECT * FROM audiobooks WHERE id = ?;'
                cr = conn.cursor()
                cr.execute(query, (audiobook_id,))
                audiobook = cr.fetchone()
                query = '''
SELECT * FROM audiofiles WHERE audiobook_id = ? ORDER BY sequence ASC;'''
                cr.execute(query, (audiobook_id,))
                items = cr.fetchall()
                return audiobook, items

    def get_remaining_audiofiles(self, audiofile_id):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                query = '''
SELECT audiobook_id, sequence FROM audiofiles WHERE id = ?;'''
                cr = conn.cursor()
                cr.execute(query, (audiofile_id,))
                result = cr.fetchone()
                if not result:
                    return None, []
                audiobook_id, sequence = result
                query = 'SELECT * FROM audiobooks WHERE id = ?;'
                cr.execute(query, (audiobook_id,))
                audiobook = cr.fetchone()

                query = '''
SELECT
    *
FROM
    audiofiles
WHERE
    audiobook_id = ?
AND
    sequence >= ?
ORDER BY
    sequence
ASC;'''
                cr.execute(query, (audiobook_id, sequence))
                items = cr.fetchall()
                return audiobook, items

    def add_bookmark(self, audiofile_id, position):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                cr = conn.cursor()
                query = '''
SELECT id, audiobook_id, position FROM bookmarks WHERE audiofile_id = ?;'''
                cr.execute(query, (audiofile_id,))
                result = cr.fetchone()

                if result:
                    # Update existing bookmark.
                    bookmark_id, audiobook_id, old_position = result
                    query = '''
UPDATE bookmarks SET position = ? WHERE id = ?;'''
                    cr.execute(query, (position, bookmark_id))
                else:
                    # Add new bookmark.
                    query = '''
SELECT audiobook_id FROM audiofiles WHERE id = ?;'''
                    cr.execute(query, (audiofile_id,))
                    result = cr.fetchone()
                    if not result:
                        return False
                    audiobook_id, = result
                    query = '''
INSERT INTO bookmarks (
    audiofile_id,
    audiobook_id,
    position
) VALUES (?, ?, ?);'''
                    cr.execute(query, (audiofile_id, audiobook_id, position))
                    bookmark_id = cr.lastrowid
                return bookmark_id

    def get_bookmark(self, bookmark_id):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                cr = conn.cursor()
                query = 'SELECT * FROM bookmarks WHERE id = ?;'
                cr.execute(query, (bookmark_id,))
                result = cr.fetchone()
                return result if result else None

    def get_audiobook_last_bookmark(self, audiobook_id):
        with contextlib.closing(self.get_conn()) as conn:
            with conn:
                cr = conn.cursor()
                query = '''
SELECT
    *
FROM
    bookmarks AS b
INNER JOIN
    audiofiles AS a
ON
    a.id = b.audiofile_id
WHERE
    b.audiobook_id = ?
ORDER BY
    a.sequence DESC,
    b.position DESC
LIMIT
    1;'''
                cr.execute(query, (audiobook_id,))
                result = cr.fetchone()
                return result if result else None
