"""Tests for openapi_crud_gen.generator."""

import ast
from pathlib import Path

from openapi_crud_gen.crud import Resource, identify_crud
from openapi_crud_gen.generator import (
    expected_status_codes,
    generate_tests,
    module_file_name,
    path_parameter_names,
)
from openapi_crud_gen.parser import extract_endpoints, load_openapi

BASE_URL = "http://localhost:8000"


def _resources(fixtures_dir: Path, name: str = "openapi.yaml") -> dict[str, Resource]:
    return identify_crud(extract_endpoints(load_openapi(str(fixtures_dir / name))))


def _function_names(source: str) -> list[str]:
    tree = ast.parse(source)
    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]


def test_generate_tests_writes_one_module_per_resource(fixtures_dir: Path, tmp_path: Path) -> None:
    generated = generate_tests(_resources(fixtures_dir), str(tmp_path), BASE_URL)
    names = {Path(path).name for path in generated}

    assert names == {"__init__.py", "test_users_crud.py", "test_orders_crud.py"}
    assert all(Path(path).exists() for path in generated)


def test_generated_module_is_valid_python(fixtures_dir: Path, tmp_path: Path) -> None:
    generate_tests(_resources(fixtures_dir), str(tmp_path), BASE_URL)
    source = (tmp_path / "test_users_crud.py").read_text(encoding="utf-8")

    assert _function_names(source) == [
        "test_users_create",
        "test_users_read_list",
        "test_users_read_detail",
        "test_users_update",
        "test_users_delete",
    ]
    compile(source, "test_users_crud.py", "exec")


def test_generated_module_contains_client_calls_and_assertions(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    generate_tests(_resources(fixtures_dir), str(tmp_path), BASE_URL)
    source = (tmp_path / "test_users_crud.py").read_text(encoding="utf-8")

    assert 'BASE_URL = "http://localhost:8000"' in source
    assert "import requests" in source
    assert "requests.post(f\"{BASE_URL}/users\", json={})" in source
    assert "requests.get(f\"{BASE_URL}/users\")" in source
    assert "requests.delete(f\"{BASE_URL}/users/{id}\")" in source
    assert "id = None  # TODO: 替换路径参数" in source
    assert "assert response.status_code in [201]" in source
    assert "assert response.status_code in [204]" in source
    assert "# TODO: 准备请求数据" in source


def test_generated_module_uses_patch_when_document_says_so(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    generate_tests(_resources(fixtures_dir), str(tmp_path), BASE_URL)
    source = (tmp_path / "test_orders_crud.py").read_text(encoding="utf-8")

    assert _function_names(source) == ["test_orders_read_list", "test_orders_update"]
    assert "requests.patch(f\"{BASE_URL}/orders/{id}\", json={})" in source


def test_existing_files_are_skipped_without_overwrite(fixtures_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "test_users_crud.py"
    target.write_text("# hand written\n", encoding="utf-8")

    generated = generate_tests(_resources(fixtures_dir), str(tmp_path), BASE_URL)

    assert str(target) not in generated
    assert target.read_text(encoding="utf-8") == "# hand written\n"
    assert len(generated) == 2


def test_overwrite_replaces_existing_file(fixtures_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "test_users_crud.py"
    target.write_text("# hand written\n", encoding="utf-8")

    generated = generate_tests(_resources(fixtures_dir), str(tmp_path), BASE_URL, overwrite=True)

    assert str(target) in generated
    assert "hand written" not in target.read_text(encoding="utf-8")


def test_dry_run_writes_nothing(fixtures_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "nested" / "generated"

    generated = generate_tests(_resources(fixtures_dir), str(out_dir), BASE_URL, dry_run=True)

    assert len(generated) == 3
    assert not out_dir.exists()


def test_package_init_is_created_once(fixtures_dir: Path, tmp_path: Path) -> None:
    generate_tests(_resources(fixtures_dir), str(tmp_path), BASE_URL)
    init_file = tmp_path / "__init__.py"
    init_file.write_text('"""custom"""\n', encoding="utf-8")

    generated = generate_tests(
        _resources(fixtures_dir), str(tmp_path), BASE_URL, overwrite=True
    )

    assert str(init_file) not in generated
    assert init_file.read_text(encoding="utf-8") == '"""custom"""\n'


def test_no_resources_generates_nothing(tmp_path: Path) -> None:
    out_dir = tmp_path / "generated"

    assert generate_tests({}, str(out_dir), BASE_URL) == []
    assert not out_dir.exists()


def test_result_lands_in_the_requested_directory(fixtures_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "deep" / "tests"

    generated = generate_tests(_resources(fixtures_dir), str(out_dir), BASE_URL)

    assert all(Path(path).parent == out_dir for path in generated)
    assert (out_dir / "__init__.py").exists()


def test_expected_status_codes_keeps_only_success_ranges() -> None:
    responses = {"200": {}, "302": {}, "404": {}, "default": {}}

    assert expected_status_codes("read_detail", responses) == [200, 302]


def test_expected_status_codes_falls_back_per_action() -> None:
    assert expected_status_codes("create", {"400": {}}) == [201]
    assert expected_status_codes("read_list", {}) == [200]
    assert expected_status_codes("update", {}) == [200]
    assert expected_status_codes("delete", {}) == [204]


def test_path_parameter_names_returns_identifiers() -> None:
    assert path_parameter_names("/users/{id}/posts/{post-id}") == ["id", "post_id"]
    assert path_parameter_names("/users") == []


def test_body_placeholder_follows_the_method(tmp_path: Path) -> None:
    spec = {
        "paths": {
            "/notes/{id}": {
                "put": {"responses": {"200": {"description": "OK"}}},
                "delete": {"responses": {"204": {"description": "No Content"}}},
            }
        }
    }
    resources = identify_crud(extract_endpoints(spec))

    generate_tests(resources, str(tmp_path), BASE_URL)
    source = (tmp_path / "test_notes_crud.py").read_text(encoding="utf-8")

    assert 'requests.put(f"{BASE_URL}/notes/{id}", json={})' in source
    assert 'requests.delete(f"{BASE_URL}/notes/{id}")' in source


def test_test_file_name_uses_normalized_resource_name() -> None:
    resource = Resource(name="user_profiles", base_path="/user-profiles")

    assert module_file_name(resource) == "test_user_profiles_crud.py"
