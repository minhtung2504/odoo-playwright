"""Tests for the Odoo Playwright MCP helper layer."""

from pathlib import Path

import pytest

from odoo_playwright.mcp_server import (
    make_test_template,
    project_test_config,
    run_pytest,
    write_test_file,
)


def test_make_test_template_uses_feature_and_app():
    code = make_test_template("sale order validation", app="Sales")

    assert "sale order validation" in code
    assert 'odoo_ui.go_to_app("Sales")' in code
    assert "def test_feature_behavior" in code


def test_write_test_file_restricts_path_to_tests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = write_test_file("tests/test_generated.py", "def test_ok():\n    assert True")

    assert Path(result["path"]).read_text(encoding="utf-8").endswith("assert True\n")


def test_write_test_file_rejects_non_test_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="under tests"):
        write_test_file("scripts/test_generated.py", "def test_ok(): pass")


@pytest.mark.parametrize("path", ["tests/generated.py", "tests/helper.txt"])
def test_write_test_file_rejects_non_pytest_names(tmp_path, monkeypatch, path):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="test_\\*.py"):
        write_test_file(path, "def test_ok(): pass")


def test_run_pytest_rejects_unsupported_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests").mkdir()

    with pytest.raises(ValueError, match="Unsupported env key"):
        run_pytest("tests", env={"PATH": "/tmp"})


def test_project_test_config_documents_env_contract():
    config = project_test_config()

    assert "ODOO_URL" in config["required_env"]
    assert "ODOO_VERSION" in config["optional_env"]
    assert config["default_command"][-1] == "tests"
