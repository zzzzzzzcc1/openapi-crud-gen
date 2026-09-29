"""Tests for openapi_crud_gen.cli."""

import importlib.metadata
from pathlib import Path

import openapi_crud_gen
from click.testing import CliRunner

from openapi_crud_gen.cli import main


def _invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def test_help_lists_every_option() -> None:
    result = _invoke("--help")

    assert result.exit_code == 0
    for option in (
        "--output-dir",
        "--base-url",
        "--resource-filter",
        "--overwrite",
        "--dry-run",
        "--version",
    ):
        assert option in result.output


def test_version_option_reports_the_installed_version() -> None:
    result = _invoke("--version")

    assert result.exit_code == 0
    assert "openapi-crud-gen" in result.output
    assert openapi_crud_gen.__version__ in result.output


def test_package_version_matches_the_built_metadata() -> None:
    assert importlib.metadata.version("openapi-crud-gen") == openapi_crud_gen.__version__


def test_help_shows_a_copy_pasteable_example() -> None:
    result = _invoke("--help")

    assert result.exit_code == 0
    assert "openapi-crud-gen examples/openapi.yaml" in result.output


def test_next_steps_are_printed_after_generation(fixtures_dir: Path, tmp_path: Path) -> None:
    result = _invoke(
        str(fixtures_dir / "openapi.yaml"), "--output-dir", str(tmp_path / "generated")
    )

    assert result.exit_code == 0, result.output
    assert "Next steps" in result.output
    assert "TODO" in result.output
    assert "pytest" in result.output


def test_next_steps_are_omitted_in_dry_run(fixtures_dir: Path, tmp_path: Path) -> None:
    result = _invoke(
        str(fixtures_dir / "openapi.yaml"),
        "--output-dir",
        str(tmp_path / "generated"),
        "--dry-run",
    )

    assert result.exit_code == 0, result.output
    assert "Next steps" not in result.output


def test_generates_files_for_each_resource(fixtures_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "generated"

    result = _invoke(str(fixtures_dir / "openapi.yaml"), "--output-dir", str(out_dir))

    assert result.exit_code == 0, result.output
    assert (out_dir / "test_users_crud.py").exists()
    assert (out_dir / "test_orders_crud.py").exists()
    assert "Generated 3 file(s)" in result.output
    assert "users" in result.output
    assert "read_detail" in result.output


def test_base_url_option_is_written_into_the_file(fixtures_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "generated"

    result = _invoke(
        str(fixtures_dir / "openapi.json"),
        "--output-dir",
        str(out_dir),
        "--base-url",
        "http://example.test:9999",
    )

    assert result.exit_code == 0, result.output
    source = (out_dir / "test_products_crud.py").read_text(encoding="utf-8")
    assert 'BASE_URL = "http://example.test:9999"' in source


def test_dry_run_writes_nothing(fixtures_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "generated"

    result = _invoke(str(fixtures_dir / "openapi.yaml"), "--output-dir", str(out_dir), "--dry-run")

    assert result.exit_code == 0, result.output
    assert not out_dir.exists()
    assert "would write" in result.output
    assert "Dry run" in result.output


def test_existing_files_are_skipped_and_overwrite_forced(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "generated"
    out_dir.mkdir()
    target = out_dir / "test_users_crud.py"
    target.write_text("# hand written\n", encoding="utf-8")

    skipped = _invoke(str(fixtures_dir / "openapi.yaml"), "--output-dir", str(out_dir))
    assert skipped.exit_code == 0, skipped.output
    assert "skipped" in skipped.output
    assert target.read_text(encoding="utf-8") == "# hand written\n"

    forced = _invoke(str(fixtures_dir / "openapi.yaml"), "--output-dir", str(out_dir), "--overwrite")
    assert forced.exit_code == 0, forced.output
    assert "hand written" not in target.read_text(encoding="utf-8")


def test_resource_filter_keeps_only_named_resources(fixtures_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "generated"

    result = _invoke(
        str(fixtures_dir / "openapi.yaml"),
        "--output-dir",
        str(out_dir),
        "--resource-filter",
        "users",
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "test_users_crud.py").exists()
    assert not (out_dir / "test_orders_crud.py").exists()
    assert "Generated 2 file(s)" in result.output


def test_unknown_resource_filter_warns_without_failing(fixtures_dir: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "generated"

    result = _invoke(
        str(fixtures_dir / "openapi.yaml"),
        "--output-dir",
        str(out_dir),
        "--resource-filter",
        "userz",
    )

    assert result.exit_code == 0, result.output
    assert "no resource matches 'userz'" in result.output
    assert not out_dir.exists()


def test_resource_filter_accepts_the_raw_path_segment(tmp_path: Path) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "openapi: 3.0.3\n"
        "info:\n  title: T\n  version: 1.0.0\n"
        "paths:\n  /user-profiles:\n    get:\n      responses:\n"
        "        '200':\n          description: OK\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _invoke(
        str(spec), "--output-dir", str(out_dir), "--resource-filter", "user-profiles"
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "test_user_profiles_crud.py").exists()


def test_missing_file_is_a_usage_error(tmp_path: Path) -> None:
    result = _invoke(str(tmp_path / "nope.yaml"))

    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_unparseable_file_exits_with_error(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text("openapi: [3.0.3\n", encoding="utf-8")

    result = _invoke(str(broken), "--output-dir", str(tmp_path / "out"))

    assert result.exit_code == 1
    assert "error:" in result.output


def test_validation_problems_warn_but_still_generate(tmp_path: Path) -> None:
    draft = tmp_path / "draft.yaml"
    draft.write_text(
        "openapi: 3.0.3\n"
        "paths:\n  /notes:\n    get:\n      responses:\n        '200':\n          description: OK\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _invoke(str(draft), "--output-dir", str(out_dir))

    assert result.exit_code == 0, result.output
    assert "warning:" in result.output
    assert (out_dir / "test_notes_crud.py").exists()
