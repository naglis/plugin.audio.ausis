# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sqlite3

import utils


DB_FILE_NAME = 'ausis.sqlite'

AUSIS_SCHEMA = '''
CREATE TABLE IF NOT EXISTS audiobooks (
    id INTEGER NOT NULL,
    title VARCHAR(256) NOT NULL,
    author VARCHAR(256) NOT NULL,
    narrator VARCHAR(256),
    path VARCHAR NOT NULL,
    cover_path VARCHAR,           -- Relative to path
    fanart_path VARCHAR,          -- Relative to path
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
);
'''


class DatabaseMigrationError(Exception):
    '''Exception raised when a migration fails.'''


class Database(object):

    SCHEMA = None

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
        self._conn = sqlite3.connect(
            self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute('PRAGMA foreign_keys;')
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


class MigratableDatabase(Database):

    VERSION = None
    MIGRATIONS = tuple()

    def initialize(self):
        super(MigratableDatabase, self).initialize()
        if self.VERSION is None:
            raise ValueError('Database VERSION must be set')
        # Create a separate table to store database version.
        self.cr.execute('''
        CREATE TABLE IF NOT EXISTS versions (
            id INTEGER PRIMARY KEY,
            database_version INTEGER NOT NULL
        );''')
        # Write current database version.
        self.cr.execute('''
        INSERT OR REPLACE INTO versions (
            id, database_version
        ) VALUES (
            1, :version
        );''', {'version': self.VERSION})
        # Run migrations.
        self.migrate()

    def get_version(self):
        self.cr.execute('SELECT database_version FROM versions WHERE id = 1;')
        return utils.first_of(self.cr.fetchone())

    def migrate(self):
        for version, migration_func in self.MIGRATIONS:
            current_version = self.get_version()
            if version > current_version:
                try:
                    migration_func(self.cr)
                except Exception as e:
                    raise DatabaseMigrationError(e)


class AusisDatabase(MigratableDatabase):

    VERSION = 0
    SCHEMA = AUSIS_SCHEMA
    MIGRATIONS = tuple()

    def add_audiobook(self, author, title, path, files, narrator=None,
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
        self.cr.execute(query, locals())
        audiobook_id = self.cr.lastrowid

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
        self.cr.executemany(query, items)
        return audiobook_id

    def get_all_audiobooks(self):
        query = '''
        SELECT
            a.*,
            a.date_added,
            SUM(f.duration) AS duration,
            b.last_played   -- Here, even though bookmarks.date_added
                            -- is a TIMESTAMP, it will not be cast to
                            -- datetime.datetime by sqlite3.
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
            f.audiobook_id
        ;'''
        self.cr.execute(query)
        return self.cr.fetchall()

    def get_audiobook(self, audiobook_id):
        query = 'SELECT * FROM audiobooks WHERE id = :audiobook_id;'
        self.cr.execute(query, locals())
        audiobook = self.cr.fetchone()
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
        self.cr.execute(query, locals())
        return audiobook, self.cr.fetchall()

    def get_remaining_audiofiles(self, audiofile_id):
        query = '''
        SELECT audiobook_id, sequence FROM audiofiles WHERE id = :audiofile_id
        ;'''
        self.cr.execute(query, locals())
        result = self.cr.fetchone()
        if not result:
            return None, []
        audiobook_id, sequence = result
        query = 'SELECT * FROM audiobooks WHERE id = :audiobook_id;'
        self.cr.execute(query, locals())
        audiobook = self.cr.fetchone()

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
            sequence ASC
        ;'''
        self.cr.execute(query, locals())
        return audiobook, self.cr.fetchall()

    def add_bookmark(self, audiofile_id, position):
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
        self.cr.execute(query, locals())
        result = self.cr.fetchone()

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
            self.cr.execute(query, locals())
        else:
            # Add new bookmark.
            query = '''
            SELECT
                audiobook_id
            FROM
                audiofiles
            WHERE id = :audiofile_id
            ;'''
            self.cr.execute(query, locals())
            result = self.cr.fetchone()
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
            self.cr.execute(query, locals())
            bookmark_id = self.cr.lastrowid
        return bookmark_id

    def get_bookmark(self, bookmark_id):
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
        self.cr.execute(query, locals())
        result = self.cr.fetchone()
        return result if result else None

    def get_audiobook_last_bookmark(self, audiobook_id):
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
            1
        ;'''
        self.cr.execute(query, locals())
        result = self.cr.fetchone()
        return result if result else None

    def get_audiobook_by_path(self, path):
        query = '''
        SELECT
            id
        FROM
            audiobooks
        WHERE
            path = :path
        LIMIT
            1
        ;'''
        self.cr.execute(query, locals())
        result = self.cr.fetchone()
        return utils.first_of(result) if result else None

    def get_cover(self, audiobook_id):
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
        self.cr.execute(query, locals())
        result = self.cr.fetchone()
        return utils.first_of(result) if result else None

    def set_cover(self, audiobook_id, cover_path):
        query = '''
        UPDATE
            audiobooks
        SET
            cover_path = :cover_path
        WHERE
            id = :audiobook_id
        ;'''
        self.cr.execute(query, locals())

    def get_fanart(self, audiobook_id):
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
        self.cr.execute(query, locals())
        result = self.cr.fetchone()
        return utils.first_of(result) if result else None

    def set_fanart(self, audiobook_id, fanart_path):
        query = '''
        UPDATE
            audiobooks
        SET
            fanart_path = :fanart_path
        WHERE
            id = :audiobook_id
        ;'''
        self.cr.execute(query, locals())
