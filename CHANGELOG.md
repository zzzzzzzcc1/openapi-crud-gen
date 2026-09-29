# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `examples/mock_api.py`: a standard-library stub backend so the generated tests can be
  run green without a real API (quickstart helper, not part of the wheel).
- CLI prints a `Next steps` block after generating (fill TODOs, start the API or change
  `--base-url`, run pytest).
- `--help` now ends with a copy-pasteable example command.
- `--version` flag reporting the installed version.
- `docs/TUTORIAL.md`: end-to-end walkthrough (start a service, `--dry-run`, generate, read the
  failing run, fill the TODOs, go green, reuse ids with a fixture, env-var `BASE_URL`, CI hookup).
- `examples/tutorial/`: a strict stateful sample backend plus its OpenAPI document, so the
  tutorial can show why the generated TODOs decide pass or fail.

### Changed

- README gained a 60-second quickstart and an FAQ covering connection errors, missing
  `requests`, `id = None` placeholders, status-code mismatches and skip/overwrite behaviour.
- Packaging metadata now uses PEP 639 (`license = "MIT"` plus `license-files`), so the wheel
  carries `License-Expression` and `License-File`; the deprecated license classifier is gone.
- README install section covers both paths, including the one-command
  `pip install "openapi-crud-gen[dev]"` that also brings `pytest` and `requests`; the PyPI
  section is now a release checklist.
- `pytest` and `requests` moved from the `dev` extra into the core dependencies, so a bare
  `pip install openapi-crud-gen` is enough to generate *and* run the generated tests.
  The `dev` extra now only adds `pytest-cov`.

## [0.1.0] - 2026-09-29

### Added

- CLI `openapi-crud-gen` with `--output-dir`, `--base-url`, `--resource-filter`,
  `--overwrite` and `--dry-run`.
- OpenAPI 3.0 / 3.1 loading from YAML or JSON, with advisory
  `openapi-spec-validator` checks.
- CRUD recognition for collection and detail paths (`create`, `read_list`,
  `read_detail`, `update`, `delete`).
- Jinja2 template rendering one `test_<resource>_crud.py` per resource, using
  pytest and requests with TODO markers for business data.
- Rich summary output and skip/overwrite reporting.
- Unit tests with a 80% coverage gate and a GitHub Actions workflow.
