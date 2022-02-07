# Patches storage
We store patches inside a SQLite3 database, encoded as raw Midi.

``` {.python file=nymphescc/db.py}
from xdg import xdg_config_home
import sqlite3

db_schema = """
create table if not exists "snapshots"
    ( "id" integer primary key autoincrement
    , "group" integer not null
       references "groups" ("id") on delete cascade
    , "name" text not null
    , "tags" text
    , "date" text default current_timestamp
    , "midi" blob not null );

create table if not exists "groups"
    ( "id" integer primary key autoincrement
    , "name" text not null );
"""

class NymphesDB:
    def __init__(self, path=None):
        if path is None:
            path = xdg_config_home() / "nymphescc" / "patches.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._cursor = self._connection.cursor()
        self._cursor.executescript(db_schema)
        self._connection.commit()

    def new_group(self, name):
        self._cursor.execute(
            "insert into \"groups\" (\"name\") values (?)",
            (name,))
        self._connection.commit()

    def new_snapshot(self, group_id, name, midi):
        self._cursor.execute(
            "insert into \"snapshots\" (\"group\", \"name\", \"midi\") values (?, ?, ?)",
            (group_id, name, midi))
        self._connection.commit()

    def group(self, group_id):
        members = self._cursor.execute("""
            select "id", "name", "tags", "date" from "snapshots"
            where "group" is ?""", (group_id,))
        return members.fetchall()

    def tree(self):
        groups = self._cursor.execute(
            "select \"id\", \"name\" from \"groups\"").fetchall()
        return [(gid, name, self.group(gid)) for gid, name in groups]

    def load_midi(self, snapshot_id):
        return self._cursor.execute("""
            select "midi" from "snapshots"
            where "id" is ?""", (snapshot_id,)).fetchone()[0]

    def close(self):
        self._connection.close()
```
