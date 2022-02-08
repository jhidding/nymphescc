# ~\~ language=Python filename=nymphescc/db.py
# ~\~ begin <<lit/patch-db.md|nymphescc/db.py>>[0]
from xdg import xdg_config_home
import sqlite3
from dataclasses import dataclass
from datetime import datetime


db_schema = """
create table if not exists "snapshots"
    ( "id" integer primary key autoincrement
    , "group" integer not null
       references "groups" ("id") on delete cascade
    , "date" text default current_timestamp
    , "midi" blob not null );

create table if not exists "groups"
    ( "id" integer primary key autoincrement
    , "name" text not null
    , "description" text
    , "tags" text );
"""


@dataclass
class Snapshot:
    key: int
    date: datetime
    midi: bytes


@dataclass
class Group:
    key: int
    name: str
    description: str
    tags: list[str]
    snapshots: list[Snapshot]


class NymphesDB:
    def __init__(self, path=None):
        if path is None:
            path = xdg_config_home() / "nymphescc" / "patches.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._cursor = self._connection.cursor()
        self._cursor.executescript(db_schema)
        self._connection.commit()

    def new_group(self, name:str, description: str, tags: list[str]) -> int:
        self._cursor.execute("""
            insert into "groups" ("name", "description", "tags")
            values (?, ?, ?)""", (name, description, ",".join(tags)))
        self._connection.commit()
        return self._cursor.lastrowid

    def new_snapshot(self, group_id, midi):
        self._cursor.execute("""
            insert into "snapshots" ("group", "midi")
            values (?, ?, ?)""", (group_id, midi))
        self._connection.commit()
        return self._cursor.lastrowid

    def group(self, group_id):
        members = self._cursor.execute("""
            select "id", "date", "midi" from "snapshots"
            where "group" is ?""", (group_id,))
        return [Snapshot(key, datetime.fromtimestamp(date), midi)
                for key, date, midi in members.fetchall()]

    def snapshot(self, snap_id):
        key, date, midi = self._cursor.execute("""
            select "id", "date", "midi" from "snapshots"
            where "id" is ?""", (snap_id,)).fetchone()
        return Snapshot(key, datetime.fromtimestamp(date), midi)

    def tree(self):
        groups = self._cursor.execute("""
            select * from "groups"
            """).fetchall()
        return [Group(key, name, description, tags.split(","), self.group(gid))
                for gid, name in groups]

    def close(self):
        self._connection.close()


def test_db(tmp_path):
    from datetime import timedelta, datetime
    db = NymphesDB(tmp_path / "test.db")
    group_id = db.new_group("hello")
    snap_id = db.new_snapshow(group_id, b"123")
    s = db.snapshot(snap_id)
    assert s.midi = b"123"
    assert datetime.now() - s.date < timedelta(seconds=1)
# ~\~ end
