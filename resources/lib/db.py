# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sqlite3

import utils


DB_FILE_NAME = 'ausis.sqlite'


class AudioBookDB(object):

    def __init__(self, db_path):
        self._db_path = db_path

    def get_conn(self):
        conn = sqlite3.connect(
            self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys;')
        with conn:
            cr = conn.cursor()
            init_db(cr)
        return conn


def init_db(cr):
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
    date_added TIMESTAMP DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE (id)
);
CREATE TABLE IF NOT EXISTS audiofiles (
    id INTEGER NOT NULL,
    audiobook_id INTEGER,
    title VARCHAR,
    file_path VARCHAR NOT NULL, -- Relative to audiobook.path
    duration REAL,
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
    position REAL,
    date_added TIMESTAMP DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE (id),
    FOREIGN KEY(audiofile_id) REFERENCES audiofiles (id) ON DELETE CASCADE,
    FOREIGN KEY(audiobook_id) REFERENCES audiobooks (id) ON DELETE CASCADE
);''')


def add_audiobook(cr, author, title, path, files, narrator=None,
                  cover_path=None, fanart_path=None, summary=None):
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
    :author,
    :title,
    :narrator,
    :path,
    :cover_path,
    :fanart_path,
    :summary,
    DATETIME('now')
);'''
    cr.execute(query, locals())
    audiobook_id = cr.lastrowid

    items = []
    for sequence, item in enumerate(files, start=1):
        title, file_path, duration, size = item
        items.append({
            'audiobook_id': audiobook_id,
            'title': title,
            'file_path': file_path,
            'duration': duration,
            'sequence': sequence,
            'size': size,
        })

    query = '''
INSERT INTO audiofiles (
    audiobook_id,
    title,
    file_path,
    duration,
    sequence,
    size
) VALUES (
    :audiobook_id,
    :title,
    :file_path,
    :duration,
    :sequence,
    :size
);'''
    cr.executemany(query, items)

    return audiobook_id


def audiobook_exists(cr, subdir):
    query = '''
SELECT
    *
FROM
    audiobooks
WHERE
    path = :path
LIMIT
    1;'''
    cr.execute(query, {'path': subdir})
    res = cr.fetchone()
    return bool(res)


def get_all_audiobooks(cr):
    query = '''
SELECT
    a.*,
    a.date_added,
    SUM(f.duration) AS duration,
    b.last_played -- Here, even though bookmarks.date_added is a TIMESTAMP,
                  -- it will not be cast to datetime.datetime by sqlite3.
FROM
    audiobooks AS a
JOIN
    audiofiles AS f
ON
    a.id = f.audiobook_id
LEFT JOIN (
    SELECT
        bookmarks.audiobook_id,
        MAX(bookmarks.date_added) AS last_played
    FROM
        bookmarks
    GROUP BY
        bookmarks.audiobook_id
    ORDER By
        date_added DESC
    ) AS b
ON
    a.id = b.audiobook_id
GROUP BY
    f.audiobook_id;
'''
    cr.execute(query)
    return cr.fetchall()


def get_audiobook(cr, audiobook_id):
    query = 'SELECT * FROM audiobooks WHERE id = :audiobook_id;'
    cr.execute(query, locals())
    audiobook = cr.fetchone()
    query = '''
SELECT
    *
FROM
    audiofiles
WHERE
    audiobook_id = :audiobook_id
ORDER BY
    sequence ASC
;'''
    cr.execute(query, locals())
    return audiobook, cr.fetchall()


def get_remaining_audiofiles(cr, audiofile_id):
    query = '''
SELECT audiobook_id, sequence FROM audiofiles WHERE id = :audiofile_id;'''
    cr.execute(query, locals())
    result = cr.fetchone()
    if not result:
        return None, []
    audiobook_id, sequence = result
    query = 'SELECT * FROM audiobooks WHERE id = :audiobook_id;'
    cr.execute(query, locals())
    audiobook = cr.fetchone()

    query = '''
SELECT
    *
FROM
    audiofiles
WHERE
    audiobook_id = :audiobook_id
AND
    sequence >= :sequence
ORDER BY
    sequence
ASC;'''
    cr.execute(query, locals())
    return audiobook, cr.fetchall()


def add_bookmark(cr, audiofile_id, position):
    query = '''
SELECT
    id,
    audiobook_id,
    position
FROM
    bookmarks
WHERE
    audiofile_id = :audiofile_id
;'''
    cr.execute(query, locals())
    result = cr.fetchone()

    if result:
        # Update existing bookmark.
        bookmark_id, audiobook_id, old_position = result
        query = '''
UPDATE
    bookmarks
SET
    position = :position,
    date_added = DATETIME('now')
WHERE
    id = :bookmark_id
;'''
        cr.execute(query, locals())
    else:
        # Add new bookmark.
        query = '''
SELECT
    audiobook_id
FROM
    audiofiles
WHERE id = :audiofile_id
;'''
        cr.execute(query, locals())
        result = cr.fetchone()
        if not result:
            return False
        audiobook_id, = result
        query = '''
INSERT INTO bookmarks (
    audiofile_id,
    audiobook_id,
    position,
    date_added
) VALUES (
    :audiofile_id,
    :audiobook_id,
    :position,
    DATETIME('now')
);'''
        cr.execute(query, locals())
        bookmark_id = cr.lastrowid
    return bookmark_id


def get_bookmark(cr, bookmark_id):
    query = '''
SELECT
    b.*,
    a.title
FROM
    bookmarks AS b
INNER JOIN
    audiofiles AS a
ON
    a.id = b.audiofile_id
WHERE
    b.id = :bookmark_id
;'''
    cr.execute(query, locals())
    result = cr.fetchone()
    return result if result else None


def get_audiobook_last_bookmark(cr, audiobook_id):
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
    b.audiobook_id = :audiobook_id
ORDER BY
    a.sequence DESC,
    b.position DESC
LIMIT
    1;'''
    cr.execute(query, locals())
    result = cr.fetchone()
    return result if result else None


def get_audiobook_by_path(cr, path):
    query = '''
SELECT
    id
FROM
    audiobooks
WHERE
    path = :path
LIMIT
    1;'''
    cr.execute(query, locals())
    result = cr.fetchone()
    return utils.first_of(result) if result else None


def get_cover(cr, audiobook_id):
    query = '''
SELECT
    cover_path
FROM
    audiobooks
WHERE
    id = :audiobook_id
LIMIT
    1
;'''
    cr.execute(query, locals())
    result = cr.fetchone()
    return utils.first_of(result) if result else None


def set_cover(cr, audiobook_id, cover_path):
    query = '''
UPDATE
    audiobooks
SET
    cover_path = :cover_path
WHERE
    id = :audiobook_id
;'''
    cr.execute(query, locals())


def get_fanart(cr, audiobook_id):
    query = '''
SELECT
    fanart_path
FROM
    audiobooks
WHERE
    id = :audiobook_id
LIMIT
    1
;'''
    cr.execute(query, locals())
    result = cr.fetchone()
    return utils.first_of(result) if result else None


def set_fanart(cr, audiobook_id, fanart_path):
    query = '''
UPDATE
    audiobooks
SET
    fanart_path = :fanart_path
WHERE
    id = :audiobook_id
;'''
    cr.execute(query, locals())
