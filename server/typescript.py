from __future__ import annotations
from collections.abc import (
    Callable,
    Collection,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Set,
)
from inspect import get_annotations
from types import NoneType, UnionType
from typing import Any, Literal, get_origin
import msgspec


def typescript_literal(obj: Any) -> str:
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, (int, float, str)):
        return repr(obj)
    raise TypeError(obj)


StructCallback = Callable[[type[msgspec.Struct]], None]


def typescript_type(obj: Any, struct: StructCallback) -> str:
    if obj is msgspec.UnsetType:
        return "undefined"
    if obj is NoneType or obj is None:
        return "null"
    if obj is bool:
        return "boolean"
    if obj is int:
        return "number"
    if obj is float:
        return "number"
    if obj is str:
        return "string"
    if obj is bytes:
        return "string"
    if obj is bytearray:
        return "string"
    if get_origin(obj) is tuple:
        if len(obj.__args__) == 2 and obj.__args__[1] is ...:
            return typescript_type(obj.__args__[0], struct) + "[]"
        return "[" + ",".join(typescript_type(x, struct) for x in obj.__args__) + "]"
    if get_origin(obj) in (
        list,
        set,
        frozenset,
        Collection,
        Sequence,
        MutableSequence,
        MutableSet,
        Set,
    ):
        return typescript_type(obj.__args__[0], struct) + "[]"
    if get_origin(obj) in (dict, Mapping, MutableMapping):
        k = typescript_type(obj.__args__[0], struct)
        v = typescript_type(obj.__args__[1], struct)
        return f"{{[index: {k}]: {v}}}"
    if get_origin(obj) is Literal:
        return "|".join(typescript_literal(x) for x in obj.__args__)
    if get_origin(obj) is UnionType:
        return "|".join(typescript_type(x, struct) for x in obj.__args__)
    if issubclass(obj, msgspec.Struct):
        struct(obj)
        return obj.__name__
    raise TypeError(obj)


def typescript_struct(obj: type[msgspec.Struct], struct: StructCallback):
    ann = get_annotations(obj)
    return (
        f"export interface {obj.__name__} {{"
        + ";".join(
            f"{field}: {typescript_type(fieldtype, struct)}"
            for field, fieldtype in ann.items()
        )
        + "}"
    )


def typescript_post(
    name: str,
    path: str,
    args: list[tuple[str, Any]],
    returns: Any,
    struct: StructCallback,
):
    argtypes = ",".join(
        f"{arg}:{typescript_type(argtype, struct)}" for arg, argtype in args
    )
    return (
        f"export async function {name}({argtypes}) {{"
        + f"return (await client.post({path!r},"
        + "{"
        + ",".join(x for x, _ in args)
        + "}"
        + f")) as HTTPResult<{typescript_type(returns, struct)}>;"
        + "}"
    )
