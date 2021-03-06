# ~\~ language=Python filename=nymphescc/db.py
# ~\~ begin <<lit/patch-db.md|nymphescc/db.py>>[0]
from xdg import xdg_config_home
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


db_schema = """
create table if not exists "snapshots"
    ( "id" integer primary key autoincrement
    , "group" integer not null
       references "groups" ("id") on delete cascade
    , "date" text default current_timestamp
    , "midi" blob not null
    , "tags" text );

create table if not exists "groups"
    ( "id" integer primary key autoincrement
    , "name" text not null
    , "description" text );
"""


@dataclass
class Snapshot:
    key: int
    timestamp: datetime
    tags: Optional[str]
    midi: bytes


@dataclass
class GroupInfo:
    key: int
    name: str
    description: Optional[str]


class NymphesDB:
    def __init__(self, path: Optional[Path] = None):
        if path is None:
            path = xdg_config_home() / "nymphescc" / "patches.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._cursor = self._connection.cursor()
        self._cursor.executescript(db_schema)
        self._connection.commit()

    def new_group(self, name: str, description: Optional[str] = None) -> int:
        self._cursor.execute("""
            insert into "groups" ("name", "description")
            values (?, ?)""", (name, description))
        self._connection.commit()
        return self._cursor.lastrowid

    def new_snapshot(self, group_id: int, midi: bytes, tags: Optional[str] = None) -> int:
        self._cursor.execute("""
            insert into "snapshots" ("group", "midi", "tags")
            values (?, ?, ?)""", (group_id, midi, tags))
        self._connection.commit()
        return self._cursor.lastrowid

    def delete_group(self, group_id: int):
        self._cursor.execute("""
            delete from "groups" where "id" = ?""", (group_id,))
        self._connection.commit()

    def group_info(self, group_id: int) -> GroupInfo:
        info = self._cursor.execute("""
            select "id", "name", "description" from "groups"
            where "id" is ?""", (group_id,))
        return GroupInfo(*info.fetchone())

    def snapshots(self, group_id: int) -> list[Snapshot]:
        members = self._cursor.execute("""
            select "id", "date", "midi", "tags" from "snapshots"
            where "group" is ?""", (group_id,))
        return [Snapshot(key, datetime.fromisoformat(date), tags, midi)
                for key, date, midi, tags in members.fetchall()]

    def set_name(self, group_id, name):
        self._cursor.execute("""
            update "groups" set "name" = ?
            where "id" = ?""", (name, group_id))
        self._connection.commit()

    def set_description(self, group_id, name):
        self._cursor.execute("""
            update "groups" set "description" = ?
            where "id" = ?""", (name, group_id))
        self._connection.commit()

    def groups(self):
        groups = self._cursor.execute("""
            select * from "groups"
            """)
        return [GroupInfo(*g) for g in groups.fetchall()]

    def snapshot(self, snap_id: int) -> Snapshot:
        key, date, midi, tags = self._cursor.execute("""
            select "id", "date", "midi", "tags" from "snapshots"
            where "id" is ?""", (snap_id,)).fetchone()
        return Snapshot(key, datetime.fromisoformat(date), tags, midi)

    def tree(self) -> list[tuple[GroupInfo, list[Snapshot]]]:
        groups = self._cursor.execute("""
            select * from "groups"
            """).fetchall()
        return [(GroupInfo(key, name, description), self.snapshots(key))
                for key, name, description in groups]

    def close(self):
        self._connection.close()


def test_db(tmp_path: Path):
    from datetime import timedelta, datetime
    db = NymphesDB(tmp_path / "test.db")
    group_id = db.new_group("hello", "test 123")
    assert isinstance(group_id, int)
    snap_id = db.new_snapshot(group_id, b"123")
    assert isinstance(snap_id, int)
    s = db.snapshot(snap_id)
    assert s.midi == b"123"
    assert datetime.utcnow() - s.timestamp < timedelta(seconds=2)
    t = db.tree()
    assert t[0][0].name == "hello"
    assert len(t[0][1]) == 1
# ~\~ end
