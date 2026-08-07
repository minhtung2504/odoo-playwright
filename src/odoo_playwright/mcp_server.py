"""MCP server for agent-friendly Odoo UI test generation and execution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ALLOWED_ENV_KEYS = {
    "ODOO_URL",
    "ODOO_USER",
    "ODOO_PASSWORD",
    "ODOO_DB",
    "ODOO_VERSION",
    "HEADLESS",
    "SLOW_MO",
}

DEFAULT_TEST = """\
def test_feature_behavior(odoo_ui):
    \"\"\"Describe the user-visible behavior this test verifies.\"\"\"
    odoo_ui.go_to_app(\"{app}\")

    # TODO: navigate to the changed feature and perform the user action.
    # Example:
    # odoo_ui.go_to_menu(\"Configuration\", \"Settings\")
    # odoo_ui.click_create()
    # odoo_ui.fill_field(\"name\", \"MCP smoke test\")
    # odoo_ui.click_save()

    assert odoo_ui.page.locator(\".o_content\").count() > 0
"""


def _repo_root() -> Path:
    return Path.cwd().resolve()


def _resolve_under_repo(path: str, *, must_be_test: bool = False) -> Path:
    root = _repo_root()
    candidate = (root / path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside the repository: {path}") from exc

    if must_be_test:
        try:
            candidate.relative_to(root / "tests")
        except ValueError as exc:
            raise ValueError("Test files must be written under tests/") from exc
        if candidate.suffix != ".py" or not candidate.name.startswith("test_"):
            raise ValueError("Test file names must match tests/**/test_*.py")

    return candidate


def _filtered_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in (overrides or {}).items():
        if key not in ALLOWED_ENV_KEYS:
            allowed = ", ".join(sorted(ALLOWED_ENV_KEYS))
            raise ValueError(f"Unsupported env key {key!r}. Allowed keys: {allowed}")
        env[key] = str(value)
    return env


def _bounded_timeout(timeout_seconds: int) -> int:
    if timeout_seconds < 1:
        raise ValueError("timeout_seconds must be at least 1")
    return min(timeout_seconds, 600)


def make_test_template(feature: str, app: str = "Settings") -> str:
    """Create a pytest template using the odoo_ui fixture."""
    feature_doc = feature.strip() or "the changed Odoo feature"
    app_name = app.strip() or "Settings"
    return (
        '"""Playwright regression test for '
        + feature_doc.replace('"""', "'''")
        + '."""\n\n'
        + DEFAULT_TEST.format(app=app_name.replace('"', '\\"'))
    )


def write_test_file(path: str, code: str, overwrite: bool = False) -> dict[str, Any]:
    """Write a pytest file safely under tests/."""
    target = _resolve_under_repo(path, must_be_test=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code.rstrip() + "\n", encoding="utf-8")
    return {"path": str(target), "bytes": target.stat().st_size}


def run_pytest(
    path: str = "tests",
    extra_args: list[str] | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run pytest without shell expansion and return structured output."""
    target = _resolve_under_repo(path)
    command = [sys.executable, "-m", "pytest", str(target)] + list(extra_args or [])
    completed = subprocess.run(
        command,
        cwd=_repo_root(),
        env=_filtered_env(env),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=_bounded_timeout(timeout_seconds),
        check=False,
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "output": completed.stdout[-20000:],
    }


def project_test_config() -> dict[str, Any]:
    """Return the Odoo test environment contract agents should use."""
    return {
        "required_env": ["ODOO_URL", "ODOO_USER", "ODOO_PASSWORD", "ODOO_DB"],
        "optional_env": ["ODOO_VERSION", "HEADLESS", "SLOW_MO"],
        "default_command": [sys.executable, "-m", "pytest", "tests"],
        "example_env": {
            "ODOO_URL": "http://localhost:8069",
            "ODOO_USER": "admin",
            "ODOO_PASSWORD": "admin",
            "ODOO_DB": "test",
            "ODOO_VERSION": "17",
            "HEADLESS": "true",
            "SLOW_MO": "0",
        },
    }


def build_server() -> Any:
    """Build the MCP server lazily so importing helpers does not require mcp."""
    try:
        from mcp.server import MCPServer
    except ImportError as exc:  # pragma: no cover - exercised by console use
        raise RuntimeError(
            "The MCP extra is not installed. Run: pip install 'odoo-playwright[mcp]'"
        ) from exc

    mcp = MCPServer("odoo-playwright")

    @mcp.tool()
    def get_test_config() -> dict[str, Any]:
        """Show Odoo Playwright environment variables and default pytest command."""
        return project_test_config()

    @mcp.tool()
    def create_test_template(feature: str, app: str = "Settings") -> str:
        """Create a pytest template for a feature an agent just implemented."""
        return make_test_template(feature=feature, app=app)

    @mcp.tool()
    def write_test(path: str, code: str, overwrite: bool = False) -> dict[str, Any]:
        """Write a generated pytest file under tests/**/test_*.py."""
        return write_test_file(path=path, code=code, overwrite=overwrite)

    @mcp.tool()
    def run_tests(
        path: str = "tests",
        extra_args: list[str] | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        """Run Odoo Playwright pytest tests and return command, exit code, and output."""
        return run_pytest(
            path=path,
            extra_args=extra_args,
            env=env,
            timeout_seconds=timeout_seconds,
        )

    return mcp


def main() -> None:
    """Run the MCP server over stdio."""
    build_server().run()


if __name__ == "__main__":
    main()
