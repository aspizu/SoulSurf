import secrets
from datetime import datetime

import msgspec


class Session(msgspec.Struct):
    id: str
    username: str
    userid: int
    role: int
    created: datetime

    def is_expired(self) -> bool:
        return (datetime.now() - self.created).days > 30


class Sessions:
    def __init__(self):
        self.sessions: dict[str, Session] = {}
        self.users: dict[str, str] = {}

    def create(self, username: str, userid: int, role: int):
        self.removebyusername(username)
        session = Session(
            secrets.token_urlsafe(), username, userid, role, datetime.now()
        )
        self.users[username] = session.id
        self.sessions[session.id] = session
        return session

    def byid(self, id: str):
        if session := self.sessions.get(id):
            if session.is_expired():
                self.sessions.pop(id)
                return None
            return session

    def byusername(self, username: str):
        if id := self.users.get(username):
            return self.byid(id)

    def removebyid(self, id: str):
        if session := self.sessions.get(id):
            self.sessions.pop(id)
            self.users.pop(session.username)

    def removebyusername(self, username: str):
        if id := self.users.get(username):
            self.sessions.pop(id)
            self.users.pop(username)
