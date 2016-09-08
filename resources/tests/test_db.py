from __future__ import unicode_literals

import os
import sqlite3
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from lib import db


class TestDatabase(unittest.TestCase):

    def setUp(self):
        super(TestDatabase, self).setUp()

    def test_tables_are_created(self):
        database = db.AudioBookDB(':memory:')
        conn = database.get_conn()
        for table in ('audiobooks', 'audiofiles', 'bookmarks'):
            try:
                conn.execute('SELECT * FROM %s;' % table)
            except sqlite3.OperationalError:
                self.fail('Table: %s was not created' % table)
        conn.close()
