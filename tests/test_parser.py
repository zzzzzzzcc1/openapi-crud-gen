"""Tests for openapi_crud_gen.parser."""

from pathlib import Path

import pytest

from openapi_crud_gen.parser import (
    Endpoint,
    extract_endpoints,
    load_openapi,
    validate_spec,
)


def test_load_openapi_reads_yaml(fixtures_dir: Path) -> None:
    spec = load_openapi(str(fixtures_dir / "openapi.yaml"))

    assert spec["openapi"] == "3.0.3"
    assert spec["info"]["title"] == "Fixture API"
    assert "/users" in spec["paths"]


def test_load_openapi_reads_json(fixtures_dir: Path) -> None:
    spec = load_openapi(str(fixtures_dir / "openapi.json"))

    assert spec["openapi"] == "3.1.0"
    assert "/products/{sku}" in spec["paths"]


def test_load_openapi_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_openapi(str(tmp_path / "nope.yaml"))


def test_load_openapi_unparseable_content(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text("openapi: [3.0.3\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cannot parse"):
        load_openapi(str(broken))


def test_load_openapi_rejects_non_openapi_documents(tmp_path: Path) -> None:
    swagger = tmp_path / "swagger.json"
    swagger.write_text('{"swagger": "2.0", "info": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="OpenAPI 3.x"):
        load_openapi(str(swagger))

    listing = tmp_path / "list.yaml"
    listing.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_openapi(str(listing))


def test_validate_spec_accepts_fixtures(fixtures_dir: Path) -> None:
    assert validate_spec(load_openapi(str(fixtures_dir / "openapi.yaml"))) == []
    assert validate_spec(load_openapi(str(fixtures_dir / "openapi.json"))) == []


def test_validate_spec_reports_errors() -> None:
    errors = validate_spec({"openapi": "3.0.3", "paths": {"/x": {"get": {}}}})

    assert errors, "an incomplete document must produce validation messages"


def test_extract_endpoints_returns_operations_in_document_order(fixtures_dir: Path) -> None:
    endpoints = extract_endpoints(load_openapi(str(fixtures_dir / "openapi.yaml")))
    collected = [(e.method, e.path) for e in endpoints]

    assert collected[:2] == [("get", "/users"), ("post", "/users")]
    assert ("options", "/health") in collected
    assert all(isinstance(e, Endpoint) for e in endpoints)
    assert all(e.method == e.method.lower() for e in endpoints)


def test_extract_endpoints_skips_non_operation_keys(fixtures_dir: Path) -> None:
    endpoints = extract_endpoints(load_openapi(str(fixtures_dir / "openapi.yaml")))

    assert {e.path for e in endpoints} == {
        "/users",
        "/users/{id}",
        "/users/{id}/posts",
        "/orders",
        "/orders/{id}",
        "/health",
    }
    assert len(endpoints) == 10


def test_extract_endpoints_keeps_method_metadata(fixtures_dir: Path) -> None:
    endpoints = extract_endpoints(load_openapi(str(fixtures_dir / "openapi.yaml")))
    by_key = {(e.method, e.path): e for e in endpoints}

    create = by_key[("post", "/users")]
    assert create.operation_id == "createUser"
    assert create.summary == "Create user"
    assert create.request_body_schema == {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    assert set(create.responses) == {"201", "400"}

    detail = by_key[("get", "/users/{id}")]
    assert detail.operation_id == "getUser"
    assert detail.request_body_schema is None
    assert set(detail.responses) == {"200", "404"}


def test_extract_endpoints_merges_path_item_parameters(fixtures_dir: Path) -> None:
    endpoints = extract_endpoints(load_openapi(str(fixtures_dir / "openapi.yaml")))
    by_key = {(e.method, e.path): e for e in endpoints}

    detail_get = by_key[("get", "/users/{id}")]
    assert [(p["name"], p["in"]) for p in detail_get.parameters] == [("id", "path")]

    list_users = by_key[("get", "/users")]
    assert [(p["name"], p["in"]) for p in list_users.parameters] == [("limit", "query")]

    delete_user = by_key[("delete", "/users/{id}")]
    assert [(p["name"], p["in"]) for p in delete_user.parameters] == [("id", "path")]


def test_extract_endpoints_tolerates_missing_paths() -> None:
    assert extract_endpoints({"openapi": "3.0.3", "info": {"title": "t", "version": "1"}}) == []
    assert extract_endpoints({"paths": None}) == []


def test_extract_endpoints_operation_level_parameter_wins() -> None:
    spec = {
        "paths": {
            "/things/{id}": {
                "parameters": [{"name": "id", "in": "path", "schema": {"type": "integer"}}],
                "get": {
                    "parameters": [
                        {"name": "id", "in": "path", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            }
        }
    }

    (endpoint,) = extract_endpoints(spec)

    assert len(endpoint.parameters) == 1
    assert endpoint.parameters[0]["schema"] == {"type": "string"}


def test_extract_endpoints_handles_malformed_nodes() -> None:
    spec = {
        "paths": {
            "/broken": "not-a-path-item",
            "/weird": {
                "parameters": ["nope", {"$ref": "#/components/parameters/Id"}],
                "get": {
                    "parameters": [{"name": "q", "in": "query"}, 7],
                    "requestBody": {"content": {}},
                    "responses": [],
                },
            },
            "/media": {
                "post": {
                    "requestBody": {
                        "content": {"application/xml": {"schema": {"type": "object"}}}
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            },
            "/nocontent": {
                "post": {
                    "requestBody": {"content": {"application/json": "nope"}},
                    "responses": {"201": {"description": "Created"}},
                }
            },
        }
    }

    endpoints = extract_endpoints(spec)
    by_key = {(e.method, e.path): e for e in endpoints}

    assert len(endpoints) == 3
    assert by_key[("get", "/weird")].request_body_schema is None
    assert by_key[("get", "/weird")].responses == {}
    assert by_key[("post", "/media")].request_body_schema == {"type": "object"}
    assert by_key[("post", "/nocontent")].request_body_schema is None
