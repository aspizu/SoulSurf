import sqlite3
from typing import Any


class Row:
    def __init__(
        self, cursor: sqlite3.Cursor, row: tuple[int | float | str | bytes | None, ...]
    ):
        fields = [column[0] for column in cursor.description]
        self.row = {key: value for key, value in zip(fields, row)}

    def __getattr__(self, key: str) -> Any:
        try:
            return self.row[key]
        except KeyError:
            raise AttributeError(key) from None

    def __repr__(self):
        return repr(self.row)

    def __str__(self):
        return str(self.row)


def db():
    con = sqlite3.connect(".db")
    con.row_factory = Row
    return con, con.cursor()
