import re
from pathlib import Path
from time import time

import msgspec
from reproca import Reproca, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from .db import Row, db

USERNAME_REGEX = re.compile(r"[a-zA-Z][a-zA-Z0-9\-_]{3,128}")


def now():
    return int(time())


def is_username_ok(username: str):
    return bool(USERNAME_REGEX.fullmatch(username))


def is_password_ok(password: str):
    return len(password) >= 8


class Session(msgspec.Struct):
    id: int
    username: str
    role: int


def schema():
    con, cur = db()
    cur.executescript(
        """
        create table if not exists user (
            id integer primary key autoincrement,
            username text unique not null,
            password text not null,
            time integer not null,
            role integer not null default 0
        );

        create table if not exists box (
            id integer primary key autoincrement,
            url text unique not null,
            time integer not null,
            role integer not null default 0
        );

        create table if not exists comment (
            id integer primary key autoincrement,
            box integer not null,
            author integer not null,
            content text not null,
            time integer not null,
            role integer not null default 0,
            foreign key (box) references box(id),
            foreign key (author) references user(id)
        );
        """
    )
    con.commit()


reproca = Reproca[int, Session]()


@reproca.method
async def login(
    request: Request, response: Response, username: str, password: str
) -> bool:
    if not (is_username_ok(username) and is_password_ok(password)):
        return False
    con, cur = db()
    cur.execute("SELECT id, password, role FROM user WHERE username = ?", [username])
    row: Row | None = cur.fetchone()
    if row is None:
        return False
    if row.password != password:
        return False
    if row.role < 0:
        return False
    response.set_session(
        reproca.sessions.create(row.id, Session(row.id, username, row.role))
    )
    return True


@reproca.method
async def register(username: str, password: str) -> bool:
    if not (is_username_ok(username) and is_password_ok(password)):
        return False
    con, cur = db()
    cur.execute("SELECT id FROM user WHERE username = ?", [username])
    if cur.fetchone() is not None:
        return False
    cur.execute(
        "INSERT INTO user (username, password, time) VALUES (?, ?, ?)",
        [username, password, now()],
    )
    con.commit()
    return True


@reproca.method
async def changepwd(username: str, oldpassword: str, newpassword: str) -> bool:
    if not (is_password_ok(oldpassword) and is_password_ok(newpassword)):
        return False
    con, cur = db()
    cur.execute("SELECT id, password FROM user WHERE username = ?", [username])
    row: Row | None = cur.fetchone()
    if row is None:
        return False
    if row.password != oldpassword:
        return False
    cur.execute(
        "UPDATE user SET password = ? WHERE username = ?", [newpassword, username]
    )
    con.commit()
    reproca.sessions.remove_by_userid(row.id)
    return True


class Me(msgspec.Struct):
    username: str


@reproca.method
async def me(session: Session) -> Me:
    return Me(session.username)


class Author(msgspec.Struct):
    username: str


class Comment(msgspec.Struct):
    author: Author
    content: str
    time: int


class Box(msgspec.Struct):
    id: int
    time: int
    comments: list[Comment]


@reproca.method
async def box(url: str) -> Box | None:
    con, cur = db()
    cur.execute("SELECT id, time FROM box WHERE url = ?", [url])
    box = cur.fetchone()
    if box is None:
        return None
    cur.execute(
        """
        SELECT content, username, comment.time AS time
        FROM comment INNER JOIN user
        WHERE box = ?
        AND user.id = comment.author
        """,
        [box.id],
    )
    return Box(
        box.id,
        box.time,
        [
            Comment(Author(row.username), row.content, row.time)
            for row in cur.fetchall()
        ],
    )


@reproca.method
async def create_comment(session: Session, box: int, content: str) -> bool:
    if content == "" or len(content) > 1024:
        return False
    con, cur = db()
    cur.execute(
        """
        INSERT INTO comment (box, author, content, time)
        VALUES (?, ?, ?, ?) 
        """,
        [box, session.id, content, now()],
    )
    con.commit()
    return True


@reproca.method
async def create_box(session: Session, url: str) -> bool:
    if url == "" or len(url) > 1024:
        return False
    con, cur = db()
    cur.execute("SELECT id FROM box WHERE url = ?", [url])
    if cur.fetchone():
        return False
    cur.execute(
        """
        INSERT INTO box (url, time)
        VALUES (?, ?)         
        """,
        [url, now()],
    )
    con.commit()
    return True


reproca.typescript(Path("src/api.ts").open("w"))
app = reproca.build(
    debug=True,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "https://example.com",
            ],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)

schema()
