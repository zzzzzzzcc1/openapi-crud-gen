"""Tests for openapi_crud_gen.crud."""

from pathlib import Path

from openapi_crud_gen.crud import ACTION_ORDER, Resource, identify_crud, normalize_resource_name
from openapi_crud_gen.parser import extract_endpoints, load_openapi


def _resources(fixtures_dir: Path, name: str) -> dict[str, Resource]:
    return identify_crud(extract_endpoints(load_openapi(str(fixtures_dir / name))))


def test_identify_crud_maps_every_action(fixtures_dir: Path) -> None:
    resources = _resources(fixtures_dir, "openapi.yaml")

    assert list(resources) == ["users", "orders"]
    users = resources["users"]
    assert users.base_path == "/users"
    assert sorted(users.actions) == sorted(ACTION_ORDER)
    assert users.actions["create"].endpoint.method == "post"
    assert users.actions["read_list"].endpoint.path == "/users"
    assert users.actions["read_detail"].endpoint.path == "/users/{id}"
    assert users.actions["update"].endpoint.method == "put"
    assert users.actions["delete"].endpoint.method == "delete"


def test_identify_crud_uses_patch_when_put_is_absent(fixtures_dir: Path) -> None:
    orders = _resources(fixtures_dir, "openapi.yaml")["orders"]

    assert sorted(orders.actions) == ["read_list", "update"]
    assert orders.actions["update"].endpoint.method == "patch"


def test_identify_crud_ignores_non_crud_endpoints(fixtures_dir: Path) -> None:
    resources = _resources(fixtures_dir, "openapi.yaml")
    mapped = sum(len(resource.actions) for resource in resources.values())
    total = len(extract_endpoints(load_openapi(str(fixtures_dir / "openapi.yaml"))))

    # patch on /users/{id}, get on /users/{id}/posts and options on /health
    assert total - mapped == 3
    paths = [a.endpoint.path for r in resources.values() for a in r.actions.values()]
    assert all("/posts" not in path for path in paths)


def test_identify_crud_reads_json_documents(fixtures_dir: Path) -> None:
    resources = _resources(fixtures_dir, "openapi.json")

    assert list(resources) == ["products"]
    assert sorted(resources["products"].actions) == [
        "create",
        "delete",
        "read_detail",
        "read_list",
    ]


def test_put_replaces_patch_whichever_order_they_appear() -> None:
    spec = {
        "paths": {
            "/things/{id}": {
                "patch": {"responses": {"200": {"description": "OK"}}},
                "put": {"responses": {"200": {"description": "OK"}}},
            }
        }
    }

    update = identify_crud(extract_endpoints(spec))["things"].actions["update"]

    assert update.endpoint.method == "put"


def test_unsupported_shapes_are_skipped() -> None:
    spec = {
        "paths": {
            "/": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/{tenant}/users": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/users/me": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/users": {"put": {"responses": {"200": {"description": "OK"}}}},
            "/users/{id}": {
                "post": {"responses": {"201": {"description": "Created"}}},
                "head": {"responses": {"200": {"description": "OK"}}},
            },
        }
    }

    assert identify_crud(extract_endpoints(spec)) == {}


def test_normalize_resource_name() -> None:
    assert normalize_resource_name("users") == "users"
    assert normalize_resource_name("user-profiles") == "user_profiles"
    assert normalize_resource_name("v1.2") == "v1_2"
    assert normalize_resource_name("2fa") == "r_2fa"
    assert normalize_resource_name("class") == "class_"
    assert normalize_resource_name("user profiles") == "user_profiles"


def test_first_endpoint_wins_for_non_update_actions() -> None:
    spec = {
        "paths": {
            "/users": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/users/": {"get": {"responses": {"200": {"description": "OK"}}}},
        }
    }

    users = identify_crud(extract_endpoints(spec))["users"]

    assert list(users.actions) == ["read_list"]
    assert users.actions["read_list"].endpoint.path == "/users"
