"""Load OpenAPI 3.x documents and flatten them into endpoint records."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


@dataclass
class Endpoint:
    """A single HTTP operation declared in an OpenAPI document."""

    path: str
    method: str
    operation_id: str | None
    summary: str | None
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    responses: dict[str, Any] = field(default_factory=dict)


def load_openapi(file_path: str) -> dict[str, Any]:
    """Read a YAML or JSON OpenAPI 3.x document.

    Raises:
        OSError: the file cannot be read.
        ValueError: the content is not parseable or is not an OpenAPI 3.x mapping.
    """
    path = Path(file_path)
    raw = path.read_text(encoding="utf-8")

    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        try:
            document = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError(f"cannot parse {path}: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError(f"{path} does not contain an OpenAPI mapping")

    version = document.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        raise ValueError(
            f"{path} is not an OpenAPI 3.x document "
            f"(found 'openapi: {version}', 'swagger: {document.get('swagger')}')"
        )

    return document


def validate_spec(spec: dict[str, Any]) -> list[str]:
    """Validate against the OpenAPI schema; return messages (empty list means valid).

    Validation is advisory: callers warn and keep going, so any validator
    failure is flattened into plain strings here.
    """
    try:
        from openapi_spec_validator import validate
    except ImportError:  # pragma: no cover - dependency is declared in pyproject
        return []

    try:
        validate(spec)
    except Exception as exc:  # noqa: BLE001 - validator error types vary by version
        return [str(exc).strip().splitlines()[0] or exc.__class__.__name__]
    return []


def extract_endpoints(spec: dict[str, Any]) -> list[Endpoint]:
    """Flatten ``paths`` into a list of endpoints, keeping document order."""
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return []

    endpoints: list[Endpoint] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        path_level = path_item.get("parameters")
        path_level = path_level if isinstance(path_level, list) else []

        for key, operation in path_item.items():
            method = key.lower() if isinstance(key, str) else ""
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            operation_level = operation.get("parameters")
            operation_level = operation_level if isinstance(operation_level, list) else []
            summary = operation.get("summary")
            operation_id = operation.get("operationId")
            responses = operation.get("responses")

            endpoints.append(
                Endpoint(
                    path=path,
                    method=method,
                    operation_id=operation_id if isinstance(operation_id, str) else None,
                    summary=summary if isinstance(summary, str) else None,
                    parameters=_merge_parameters(path_level, operation_level),
                    request_body_schema=_request_body_schema(operation),
                    responses=responses if isinstance(responses, dict) else {},
                )
            )

    return endpoints


def _merge_parameters(
    path_level: list[Any], operation_level: list[Any]
) -> list[dict[str, Any]]:
    """Combine parameter lists; an operation-level entry wins over a path-level one."""
    merged: dict[Any, dict[str, Any]] = {}
    for parameter in (*path_level, *operation_level):
        if not isinstance(parameter, dict):
            continue
        name, location = parameter.get("name"), parameter.get("in")
        key = (name, location) if name and location else parameter.get("$ref", len(merged))
        merged[key] = parameter
    return list(merged.values())


def _request_body_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    """Return the JSON request body schema, or any other media type as a fallback."""
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None

    content = request_body.get("content")
    if not isinstance(content, dict) or not content:
        return None

    media = content.get("application/json")
    if not isinstance(media, dict):
        media = next((item for item in content.values() if isinstance(item, dict)), None)
        if media is None:
            return None

    # An empty mapping means "a body is declared, its schema is unspecified".
    schema = media.get("schema")
    return schema if isinstance(schema, dict) else {}
