"""Render one pytest module per resource from the parsed CRUD model."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .crud import ACTION_ORDER, Resource, normalize_resource_name

TEMPLATE_NAME = "test_crud.py.j2"

# Used when the document declares no success status code for an action.
DEFAULT_STATUS_CODES: dict[str, list[int]] = {
    "create": [201],
    "read_list": [200],
    "read_detail": [200],
    "update": [200],
    "delete": [204],
}

_PATH_PARAMETER = re.compile(r"\{([^}]+)\}")

# Methods that normally carry a payload even if the document omits a requestBody.
BODY_METHODS = frozenset({"post", "put", "patch"})


def generate_tests(
    resources: dict[str, Resource],
    output_dir: str,
    base_url: str,
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """Write one ``test_<resource>_crud.py`` per resource.

    Returns the paths that were written (or, with ``dry_run``, would be). Files
    that already exist are skipped unless ``overwrite`` is set.
    """
    if not resources:
        return []

    out_dir = Path(output_dir)
    generated: list[str] = []

    init_file = out_dir / "__init__.py"
    if not init_file.exists():
        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            init_file.write_text(
                '"""Generated test package."""\n', encoding="utf-8"
            )
        generated.append(str(init_file))

    for resource in resources.values():
        target = out_dir / module_file_name(resource)
        if target.exists() and not overwrite:
            continue
        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(render_test(resource, base_url), encoding="utf-8")
        generated.append(str(target))

    return generated


def render_test(resource: Resource, base_url: str) -> str:
    """Render the pytest module for a single resource."""
    template = _environment().get_template(TEMPLATE_NAME)
    return template.render(
        base_url=base_url,
        resource=resource,
        actions=[_action_context(resource, action) for action in _sorted_actions(resource)],
    )


def path_parameter_names(path: str) -> list[str]:
    """Return the path template parameters as valid Python identifiers."""
    return [normalize_resource_name(name) for name in _PATH_PARAMETER.findall(path)]


def expected_status_codes(action: str, endpoint_responses: dict[str, Any]) -> list[int]:
    """Return declared 2xx/3xx codes, or the per-action default when none are declared."""
    codes = set()
    for code in endpoint_responses:
        try:
            value = int(code)
        except (TypeError, ValueError):
            continue
        if 200 <= value < 400:
            codes.add(value)
    return sorted(codes) or DEFAULT_STATUS_CODES[action]


def module_file_name(resource: Resource) -> str:
    """File name generated for a resource."""
    return f"test_{resource.name}_crud.py"


def _sorted_actions(resource: Resource) -> list[str]:
    return sorted(resource.actions, key=ACTION_ORDER.index)


def _action_context(resource: Resource, action: str) -> dict[str, Any]:
    endpoint = resource.actions[action].endpoint
    return {
        "action": action,
        "function_name": f"test_{resource.name}_{action}",
        "method": endpoint.method,
        "path": endpoint.path,
        "path_params": path_parameter_names(endpoint.path),
        "has_body": endpoint.method in BODY_METHODS
        or endpoint.request_body_schema is not None,
        "status_codes": expected_status_codes(action, endpoint.responses),
    }


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
