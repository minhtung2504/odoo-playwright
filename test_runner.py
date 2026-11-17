#!/usr/bin/env python
"""Odoo 17 test runner with result analysis and reporting."""

import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class TestRunner:
    """Run and analyze test results."""

    # Test class groupings by priority
    TEST_GROUPS = {
        "Navigation": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Navigation",
        "App Navigation": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_AppNavigation",
        "View Switching": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_ViewSwitching",
        "Form Actions ⚠️": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions",
        "Field Operations ⚠️": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations",
        "Search & Filter": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_SearchAndFilter",
        "List View": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_ListViewOperations",
        "Kanban": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_KanbanOperations",
        "Modals ⚠️": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Modals",
        "Notifications": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Notifications",
        "Tabs & Actions": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_TabOperations",
        "Utilities": "tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Utilities",
    }

    # Known failing functions in Odoo 17
    KNOWN_FAILURES = {
        "test_click_delete": "Delete button moved to action menu",
        "test_fill_many2one": "Dropdown selector (.ui-autocomplete) deprecated",
        "test_close_modal": "Button selectors too generic",
        "test_go_to_tab": "Bootstrap 5 tab structure",
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: Dict[str, Dict] = {}

    def run_test_group(self, name: str, path: str) -> Dict:
        """Run a test group and return results."""
        print(f"  Testing {name}...", end=" ", flush=True)

        cmd = [
            "pytest",
            path,
            "-v",
            "--tb=no",
            "-q",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            output = result.stdout + result.stderr

            # Parse results
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            skipped = output.count(" SKIPPED")

            status = "✅" if failed == 0 else "❌"
            print(f"{status} ({passed} pass, {failed} fail, {skipped} skip)")

            return {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "output": output,
            }
        except subprocess.TimeoutExpired:
            print("⏱️  TIMEOUT")
            return {"passed": 0, "failed": 0, "skipped": 0, "error": "Timeout"}
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return {"passed": 0, "failed": 0, "skipped": 0, "error": str(e)}

    def run_all_groups(self) -> None:
        """Run all test groups."""
        print("\n" + "=" * 70)
        print("🧪 Odoo 17 AsyncOdooUI Test Suite")
        print("=" * 70 + "\n")

        total_passed = 0
        total_failed = 0
        total_skipped = 0

        for name, path in self.TEST_GROUPS.items():
            result = self.run_test_group(name, path)
            self.results[name] = result
            total_passed += result.get("passed", 0)
            total_failed += result.get("failed", 0)
            total_skipped += result.get("skipped", 0)

        # Print summary
        print("\n" + "=" * 70)
        print("📊 Summary")
        print("=" * 70)
        print(f"  Total Passed:  {total_passed} ✅")
        print(f"  Total Failed:  {total_failed} ❌")
        print(f"  Total Skipped: {total_skipped} ⏭️")
        print()

        if total_failed == 0:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. See details below.\n")
            self._print_known_issues()

        print("=" * 70 + "\n")

        # Return exit code
        sys.exit(0 if total_failed == 0 else 1)

    def _print_known_issues(self) -> None:
        """Print known Odoo 17 issues."""
        print("Known Odoo 17 Issues:")
        print("-" * 70)

        for test_name, issue in self.KNOWN_FAILURES.items():
            print(f"  • {test_name}")
            print(f"    Issue: {issue}")
            print()

        print("See ODOO17_FIXES_NEEDED.md for detailed fixes.")
        print()

    def run_single_group(self, group_name: str) -> None:
        """Run a single test group."""
        if group_name not in self.TEST_GROUPS:
            print(f"Unknown group: {group_name}")
            print(f"Available: {', '.join(self.TEST_GROUPS.keys())}")
            sys.exit(1)

        path = self.TEST_GROUPS[group_name]

        print(f"\n🧪 Running: {group_name}")
        print("=" * 70)

        cmd = ["pytest", path, "-v", "--tb=short"]
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    def list_groups(self) -> None:
        """List all test groups."""
        print("\n📋 Available Test Groups:")
        print("=" * 70)

        for i, name in enumerate(self.TEST_GROUPS.keys(), 1):
            print(f"  {i:2}. {name}")

        print("\nUsage:")
        print("  python test_runner.py <group_name>")
        print("  python test_runner.py all")
        print()

    def generate_report(self) -> None:
        """Generate a test report."""
        report_path = Path("test_report.json")

        report = {
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "summary": {
                "total_passed": sum(r.get("passed", 0) for r in self.results.values()),
                "total_failed": sum(r.get("failed", 0) for r in self.results.values()),
                "total_skipped": sum(r.get("skipped", 0) for r in self.results.values()),
            }
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Report saved to: {report_path}")


def main():
    """Main entry point."""
    runner = TestRunner(verbose="--verbose" in sys.argv or "-v" in sys.argv)

    if len(sys.argv) < 2:
        runner.list_groups()
        return

    command = sys.argv[1]

    if command == "all":
        runner.run_all_groups()
    elif command == "list":
        runner.list_groups()
    elif command in runner.TEST_GROUPS:
        runner.run_single_group(command)
    else:
        print(f"Unknown command: {command}")
        runner.list_groups()
        sys.exit(1)


if __name__ == "__main__":
    main()
