"""Command line entry point for openapi-crud-gen."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .crud import ACTION_ORDER, Resource, identify_crud
from .generator import generate_tests, module_file_name
from .parser import extract_endpoints, load_openapi, validate_spec

console = Console()

EPILOG = """\b
Example:
  openapi-crud-gen examples/openapi.yaml --output-dir tests/generated --base-url http://localhost:8000
"""


@click.command(epilog=EPILOG)
@click.version_option(__version__, "--version", prog_name="openapi-crud-gen")
@click.argument(
    "openapi_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="tests/generated",
    show_default=True,
    help="Directory that receives the generated test modules.",
)
@click.option(
    "--base-url",
    default="http://localhost:8000",
    show_default=True,
    help="Value written to BASE_URL in the generated tests.",
)
@click.option(
    "--resource-filter",
    default=None,
    help="Comma separated resource names to generate; others are skipped.",
)
@click.option("--overwrite", is_flag=True, help="Overwrite existing test modules.")
@click.option("--dry-run", is_flag=True, help="List the files that would be written.")
def main(
    openapi_file: Path,
    output_dir: Path,
    base_url: str,
    resource_filter: str | None,
    overwrite: bool,
    dry_run: bool,
) -> None:
    """Generate pytest CRUD test skeletons from an OpenAPI 3.x document."""
    try:
        spec = load_openapi(str(openapi_file))
    except (OSError, ValueError) as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise SystemExit(1) from exc

    for message in validate_spec(spec):
        console.print(f"[yellow]warning:[/yellow] {openapi_file} is not spec compliant: {message}")

    endpoints = extract_endpoints(spec)
    resources = _select(identify_crud(endpoints), resource_filter)
    ignored = len(endpoints) - sum(len(resource.actions) for resource in resources.values())

    console.print(f"Loaded [bold]{openapi_file}[/bold] (OpenAPI {spec.get('openapi')})")
    if resources:
        console.print(_summary_table(resources))
    else:
        console.print("[yellow]warning:[/yellow] no CRUD resources to generate")

    if dry_run:
        for resource in resources.values():
            console.print(f"would write {output_dir / module_file_name(resource)}")
        console.print(f"[bold]Dry run:[/bold] {len(resources)} file(s), {ignored} endpoint(s) ignored")
        return

    skipped = [
        resource
        for resource in resources.values()
        if (output_dir / module_file_name(resource)).exists() and not overwrite
    ]
    written = generate_tests(resources, str(output_dir), base_url, overwrite=overwrite)

    for resource in skipped:
        console.print(f"[yellow]skipped[/yellow] {output_dir / module_file_name(resource)} (exists)")
    console.print(
        f"[bold]Generated {len(written)} file(s)[/bold] in {output_dir} "
        f"({len(skipped)} skipped, {ignored} endpoint(s) ignored)"
    )
    if resources:
        console.print(
            "\n[bold]Next steps:[/bold]\n"
            "  1. Fill in the TODOs in the generated files "
            "(path parameters, request payload, assertions).\n"
            f"  2. Start your API at {base_url}, or regenerate with a different --base-url.\n"
            f"  3. Run: pytest {output_dir}"
        )


def _select(
    resources: dict[str, Resource], resource_filter: str | None
) -> dict[str, Resource]:
    """Keep only the resources named in ``resource_filter`` (comma separated)."""
    if not resource_filter:
        return resources

    wanted = {item.strip() for item in resource_filter.split(",") if item.strip()}
    selected: dict[str, Resource] = {}
    matched: set[str] = set()

    for name, resource in resources.items():
        path_segment = resource.base_path.strip("/")
        if name in wanted:
            selected[name] = resource
            matched.add(name)
        elif path_segment in wanted:
            selected[name] = resource
            matched.add(path_segment)

    for token in sorted(wanted - matched):
        console.print(f"[yellow]warning:[/yellow] no resource matches '{token}'")

    return selected


def _summary_table(resources: dict[str, Resource]) -> Table:
    table = Table(title="Recognized CRUD resources")
    table.add_column("Resource", style="cyan")
    table.add_column("Base path")
    table.add_column("Actions")

    for resource in resources.values():
        actions = sorted(resource.actions, key=ACTION_ORDER.index)
        table.add_row(resource.name, resource.base_path, ", ".join(actions))

    return table
