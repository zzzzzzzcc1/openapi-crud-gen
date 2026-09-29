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

### Changed

- README gained a 60-second quickstart and an FAQ covering connection errors, missing
  `requests`, `id = None` placeholders, status-code mismatches and skip/overwrite behaviour.

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
