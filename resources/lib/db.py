# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import operator
import os

from peewee import (
    CharField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

import utils

DB_FILE_NAME = 'ausis.sqlite'

duration_getter = operator.attrgetter('duration')
database = SqliteDatabase(None, autocommit=False, pragmas=(
    ('foreign_keys', 'on'),
))


class BaseModel(Model):

    class Meta:
        database = database


class Audiobook(BaseModel):
    author = CharField()
    title = CharField(null=False)
    date_added = DateTimeField(
        null=False,
        default=datetime.datetime.now,
    )
    cover = CharField(null=True)
    fanart = CharField(null=True)
    narrator = CharField(null=True)
    path = CharField(index=True, unique=True)
    summary = TextField(null=True)

    @property
    def duration(self):
        return sum(map(duration_getter, self.audiofiles))

    @property
    def cover_path(self):
        return os.path.join(self.path, self.cover) if self.cover else None

    @property
    def fanart_path(self):
        return os.path.join(self.path, self.fanart) if self.fanart else None

    @property
    def bookmarks(self):
        return (
            Bookmark.select().where(Bookmark.audiofile_id << self.audiofiles)
        )

    @property
    def last_played(self):
        bookmarks = (
            Bookmark.select().join(Audiofile).where(
                Audiofile.id == Bookmark.audiofile_id)
        ).order_by(Bookmark.date_added.desc()).limit(1)
        return utils.first_of(bookmarks).date_added if bookmarks else None

    @staticmethod
    def from_path(path):
        results = Audiobook.select().where(Audiobook.path == path)
        return utils.first_of(results) if results else None


class Audiofile(BaseModel):
    audiobook = ForeignKeyField(
        db_column='audiobook_id',
        null=False,
        rel_model=Audiobook,
        to_field='id',
        on_delete='CASCADE',
        related_name='audiofiles',
    )
    title = CharField(null=True)
    duration = IntegerField(null=True, default=0)
    file_path = CharField(null=False)
    sequence = IntegerField()
    size = IntegerField(null=True, default=0)

    class Meta:
        order_by = ('sequence',)

    @property
    def path(self):
        return os.path.join(self.audiobook.path, self.file_path)

    def get_remaining(self):
        return Audiofile.select().where(
            (Audiofile.audiobook_id == self.audiobook_id) &
            (Audiofile.sequence >= self.sequence)
        )


class Bookmark(BaseModel):
    audiofile = ForeignKeyField(
        db_column='audiofile_id',
        null=True,
        rel_model=Audiofile,
        to_field='id',
        on_delete='CASCADE',
    )
    date_added = DateTimeField(
        null=False, default=datetime.datetime.now,
    )
    position = FloatField(null=False, default=0.0)
