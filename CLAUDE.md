# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install (editable, with dev tools; add `mcp` extra for the MCP server):

```bash
pip install -e ".[dev]"
pip install -e ".[mcp]"        # optional
playwright install chromium
```

Tests need a **live Odoo instance**. Configure via environment variables (`conftest.py` reads them; nothing loads `.env` automatically, so export them in the shell):

```bash
export ODOO_URL=http://localhost:8069 ODOO_USER=admin ODOO_PASSWORD=admin ODOO_DB=test ODOO_VERSION=17
export HEADLESS=true SLOW_MO=0
```

Running tests:

```bash
pytest                                                    # everything under tests/
pytest tests/test_verify_odoo17_functions.py              # main UI suite
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions                # one class
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_save  # one test
pytest -vvs -x                                            # verbose, print output, stop on first failure
pytest -m "not integration"                               # deselect markers defined in pytest.ini
```

Wrappers (both hardcode Odoo 17 test groups; `run_odoo17_tests.sh` is bash-only):

```bash
python test_runner.py list | all | <group>
./run_odoo17_tests.sh quick | forms | list | modals | all
```

Lint / types (configured in `pyproject.toml`; the dev extras provide the tools):

```bash
ruff check .
mypy src
```

Ruff: line-length 100, rules `E,F,I,N,W,UP`, `E501` ignored. Mypy targets Python 3.9.

## Architecture

**Sync and async are parallel, hand-maintained implementations.** Almost every module has a twin:

| Sync | Async |
|------|-------|
| `ui.py` (`OdooUI`) | `ui_async.py` (`AsyncOdooUI`) |
| `views.py` (`FormView`, `ListView`, `KanbanView`) | `views_async.py` (`AsyncFormView`, ...) |
| `page.py` (`OdooPage`, `OdooSubMenu`) | `page_async.py` (`AsyncOdooPage`) |
| `wait.py` (`WaitHelper`, `wait_for_*`) | same file, `AsyncWaitHelper`, `*_async` functions |

A behavior change or selector fix usually has to be made in both halves. Check the twin before finishing an edit. `testcase.py` defines both `OdooTestCase` and `AsyncOdooTestCase`.

**Object graph.** `OdooUI(page, base_url, version)` is the root. In `__init__` it stores the Playwright `Page`, a `selectors` object from `selectors.get_selectors(version)`, and a `WaitHelper`. Views take the UI object plus a model name, for example `FormView(ui, "res.partner")`, and call back into `ui` for shared actions.

**Version-keyed selectors.** `selectors.py` holds one dict per Odoo version (`SELECTORS_V16`...`SELECTORS_V19`) keyed by logical names such as `BUTTON_SAVE` or `LIST_ROW`. `OdooSelectors.get()` falls back to the V17 dict for unknown versions. Look up selectors by key via `self.selectors.get(...)` rather than hardcoding CSS in methods. Several V17 selectors are marked in comments as unverified, and `test_runner.py` lists known-broken V17 tests (`click_delete`, `fill_many2one`, `close_modal`, `go_to_tab`).

**Tests.** `tests/conftest.py` provides:
- sync fixtures `odoo_ui` and async fixtures `async_odoo_ui`. Both log in before the test runs.
- session-scoped browser, function-scoped context and page.
- `screenshot_on_failure`, which relies on the `pytest_runtest_makereport` hook defined in the same file.

`tests/test_verify_odoo17_functions.py` is the main suite: one class per UI area, all async, using `pytest-asyncio` in auto mode. `tests/example/` and `test_create_*.py` / `test_sale_order.py` are standalone scenario tests. `tests/test_mcp_server.py` covers the MCP helper functions.

**MCP server (`src/odoo_playwright/mcp_server.py`).** Exposed as the `odoo-playwright-mcp` console script. `build_server()` registers four tools: `get_test_config`, `create_test_template`, `write_test`, `run_tests`. Safety rules live in the helpers and are tested directly:
- `write_test` only writes `tests/**/test_*.py` under the current working directory.
- `run_tests` passes env overrides only from `ALLOWED_ENV_KEYS`.
- The `mcp` library is imported lazily, so helper functions work without it.

## Gotchas

- **`OdooUI.page` is an attribute, which shadows the `page(name)` method** (`ui.py`, and similarly `ui_async.py`). The attribute is set in `__init__`, so `ui.page` is the Playwright `Page` and `ui.page("Sales")` will not work. Build page objects with `OdooPage(ui, "Sales")` / `AsyncOdooPage` instead.
- `pytest.ini` takes precedence over `[tool.pytest.ini_options]` in `pyproject.toml`. Edit `pytest.ini` for test settings. It also uses `--strict-markers`, so new markers must be registered there.
- `FIX_CHECKLIST.md` and `run_odoo17_tests.sh` refer to `ODOO17_FIXES_NEEDED.md`, which is not in the repo.
- `.env` is gitignored and not read by the code. The run script expects `ODOO_URL`, `ODOO_USER`, and `ODOO_PASSWORD` in the environment.
- `playwright-mcp.skill` is an untracked file in the repo root and is not part of the package.
