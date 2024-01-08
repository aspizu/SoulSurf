from __future__ import annotations
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from inspect import get_annotations
from os import system
from pathlib import Path
from typing import Any, Literal, Union, get_origin
import msgspec
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse
from starlette.routing import Route
from starlette.types import ExceptionHandler
from .sessions import Sessions
from .typescript import typescript_post, typescript_struct


class Response:
    def __init__(self):
        self.cookies = []
        self.headers: dict[str, str] = {}

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Literal["lax", "strict", "none"] = "lax",
    ):
        self.cookies.append(
            (
                key,
                value,
                max_age,
                expires,
                path,
                domain,
                secure,
                httponly,
                samesite,
            )
        )


class Star:
    def __init__(self, typescriptfile: Path):
        self.sessions = Sessions()
        self.routes = []
        self.typescriptfile = typescriptfile
        self.typescriptstructs = []
        self.typescript = []

    def typescriptstructcallback(self, obj: type[msgspec.Struct]):
        self.typescriptstructs.append(
            typescript_struct(obj, self.typescriptstructcallback)
        )

    def export(self, func):
        path = f"/{func.__name__}"
        ann = get_annotations(func)
        pass_request = "request" in ann
        pass_response = "response" in ann
        pass_session = (
            "OPTIONAL"
            if get_origin(ann["session"]) is Union
            else "REQUIRED"
            if "session" in ann
            else None
        )
        params = [
            (key, value)
            for key, value in ann.items()
            if key
            not in (
                "return",
                "request",
                "response",
                "session",
            )
        ]
        returns = ann["return"]
        del ann
        self.typescript.append(
            typescript_post(
                func.__name__,
                path,
                params,
                returns,
                self.typescriptstructcallback,
            )
        )

        payloadtype = msgspec.defstruct(
            "payloadtype",
            params,
        )

        async def endpoint(request: Request):
            try:
                body = msgspec.json.decode(await request.body(), type=payloadtype)
            except msgspec.ValidationError:
                return StarletteResponse(status_code=400)
            kwargs = {key: getattr(body, key) for key, _ in params}
            if pass_session:
                kwargs["session"] = None
                id = request.cookies.get("session")
                if id and (session := self.sessions.byid(id)):
                    kwargs["session"] = session
                elif pass_session == "REQUIRED":
                    return StarletteResponse(status_code=401)
            if pass_request:
                kwargs["request"] = request
            response = Response()
            if pass_response:
                kwargs["response"] = response
            body = await func(**kwargs)
            if isinstance(body, StarletteResponse):
                return body
            starletteresponse = StarletteResponse(
                msgspec.json.encode(body),
                headers=response.headers,
            )
            for cookie in response.cookies:
                starletteresponse.set_cookie(*cookie)
            return starletteresponse

        self.routes.append((path, endpoint))
        return func

    def build(
        self,
        debug: bool = False,
        middleware: Sequence[Middleware] | None = None,
        exception_handlers: Mapping[Any, ExceptionHandler] | None = None,
        on_startup: Sequence[Callable[[], Any]] | None = None,
        on_shutdown: Sequence[Callable[[], Any]] | None = None,
    ):
        self.typescriptfile.open("w").write(
            """
            import { client } from "./apiconfig.ts";
            import { HTTPResult } from "./httpclient.ts";
            """
            + "\n".join(self.typescriptstructs)
            + "\n".join(self.typescript)
            + "\n"
        )
        system(
            f"prettier --write --ignore-path /dev/null {self.typescriptfile.as_posix()}"
        )
        return Starlette(
            routes=[
                *(
                    Route(path, endpoint, methods=["POST"])
                    for path, endpoint in self.routes
                ),
                *(
                    Route(path, endpoint, methods=["GET"])
                    for path, endpoint in self.getroutes
                ),
            ],
            debug=debug,
            middleware=middleware,
            exception_handlers=exception_handlers,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
        )
