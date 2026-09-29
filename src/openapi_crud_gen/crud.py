"""Group endpoints into RESTful resources and their CRUD actions."""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass, field

from .parser import Endpoint

ACTION_ORDER = ("create", "read_list", "read_detail", "update", "delete")

# Recognized method for each action, per path shape (collection vs detail).
_COLLECTION_ACTIONS = {"post": "create", "get": "read_list"}
_DETAIL_ACTIONS = {"get": "read_detail", "put": "update", "patch": "update", "delete": "delete"}
_UPDATE_METHOD_PRIORITY = ("put", "patch")


@dataclass
class CRUDAction:
    """A recognized CRUD operation backed by one endpoint."""

    action: str
    endpoint: Endpoint


@dataclass
class Resource:
    """A RESTful resource: one collection path plus its recognized actions."""

    name: str
    base_path: str
    actions: dict[str, CRUDAction] = field(default_factory=dict)


def normalize_resource_name(segment: str) -> str:
    """Turn a path segment into a valid Python identifier usable in file and test names."""
    name = re.sub(r"[^0-9A-Za-z_]", "_", segment)
    if not name[0].isalpha() and name[0] != "_":
        name = f"r_{name}"
    if keyword.iskeyword(name):
        name = f"{name}_"
    return name


def identify_crud(endpoints: list[Endpoint]) -> dict[str, Resource]:
    """Group CRUD-shaped endpoints by resource, keeping document order."""
    resources: dict[str, Resource] = {}

    for endpoint in endpoints:
        shape, segment = _path_shape(endpoint.path)
        if shape is None:
            continue

        action = _action_for(endpoint.method, shape)
        if action is None:
            continue

        name = normalize_resource_name(segment)
        resource = resources.setdefault(name, Resource(name=name, base_path=f"/{segment}"))
        current = resource.actions.get(action)
        if current is None or _beats(endpoint.method, current.endpoint.method, action):
            resource.actions[action] = CRUDAction(action=action, endpoint=endpoint)

    return {name: resource for name, resource in resources.items() if resource.actions}


def _path_shape(path: str) -> tuple[str | None, str]:
    """Classify a path as ``collection``, ``detail`` or unrecognized."""
    segments = [segment for segment in path.split("/") if segment]
    if not segments or _is_parameter(segments[0]):
        return None, ""

    head, rest = segments[0], segments[1:]
    if not rest:
        return "collection", head
    if len(rest) == 1 and _is_parameter(rest[0]):
        return "detail", head
    return None, ""


def _is_parameter(segment: str) -> bool:
    return segment.startswith("{") and segment.endswith("}")


def _action_for(method: str, shape: str) -> str | None:
    mapping = _COLLECTION_ACTIONS if shape == "collection" else _DETAIL_ACTIONS
    return mapping.get(method)


def _beats(candidate: str, current: str, action: str) -> bool:
    """Decide whether a later endpoint replaces the one already recorded."""
    if action != "update":
        return False
    return _UPDATE_METHOD_PRIORITY.index(candidate) < _UPDATE_METHOD_PRIORITY.index(current)
