"""Pytest configuration — loads .env so API keys are available."""

import datetime
import os
import subprocess
import sys
import time

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Automatic test-result logging plugin
# Records results to tests/.last_run after every run and diffs vs baseline.
# ---------------------------------------------------------------------------

_LAST_RUN = os.path.join(os.path.dirname(__file__), ".last_run")

_results = {"passed": [], "failed": [], "skipped": []}
_start_time = None
_e2e_included = False


def _git_info():
    """Return 'abc1234' or 'abc1234 (dirty)'."""
    try:
        root = os.path.dirname(os.path.dirname(__file__))
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        return f"{commit} (dirty)" if dirty else commit
    except Exception:
        return "unknown"


def _read_previous():
    """Parse the previous .last_run into a dict."""
    if not os.path.exists(_LAST_RUN):
        return None
    out = {}
    try:
        with open(_LAST_RUN) as f:
            for line in f:
                if ": " in line:
                    k, v = line.strip().split(": ", 1)
                    out[k] = v
        return out
    except Exception:
        return None


def _int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


# ---- pytest hooks --------------------------------------------------------

def pytest_sessionstart(session):
    global _start_time
    _start_time = time.time()


def pytest_runtest_logreport(report):
    global _e2e_included
    if report.when == "call":
        if report.passed:
            _results["passed"].append(report.nodeid)
        elif report.failed:
            _results["failed"].append(report.nodeid)
        elif report.skipped:
            _results["skipped"].append(report.nodeid)
    elif report.when == "setup" and report.skipped:
        _results["skipped"].append(report.nodeid)
    if "test_e2e_real_llm" in report.nodeid:
        _e2e_included = True


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    passed = len(_results["passed"])
    failed = len(_results["failed"])
    skipped = len(_results["skipped"])
    total = passed + failed + skipped

    # Don't log if no tests actually ran (e.g. --collect-only)
    if total == 0:
        return

    duration = time.time() - _start_time if _start_time else 0
    commit = _git_info()
    args = config.invocation_params.args or []
    command = f"{sys.executable} -m pytest {' '.join(str(a) for a in args)}".strip()

    # ---- read previous baseline before overwriting -----------------------
    previous = _read_previous()

    # ---- write new .last_run ---------------------------------------------
    lines = [
        f"passed: {passed}",
        f"failed: {failed}",
        f"skipped: {skipped}",
        f"date: {datetime.date.today().isoformat()}",
        f"commit: {commit}",
        f"duration: {duration:.1f}s",
        f"e2e: {'included' if _e2e_included else 'excluded'}",
        f"command: {command}",
    ]
    if failed:
        lines.append(f"failed_tests: {', '.join(_results['failed'])}")
    try:
        with open(_LAST_RUN, "w") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as exc:
        terminalreporter.write_line(f"  [testlog] could not write {_LAST_RUN}: {exc}")
        return

    # ---- print diff summary ----------------------------------------------
    tw = terminalreporter

    if previous:
        prev_p = _int(previous.get("passed"))
        prev_f = _int(previous.get("failed"))
        prev_s = _int(previous.get("skipped"))

        tw.section("Test Log Diff (vs previous run)")

        # passed
        dp = passed - prev_p
        if dp > 0:
            tw.write_line(f"  passed:  {passed} (+{dp})", green=True)
        elif dp < 0:
            tw.write_line(f"  passed:  {passed} ({dp})", yellow=True)
        else:
            tw.write_line(f"  passed:  {passed} (unchanged)")

        # failed
        df = failed - prev_f
        if df > 0:
            tw.write_line(
                f"  REGRESSION: {df} new failure(s)  (was {prev_f}, now {failed})",
                red=True, bold=True,
            )
            prev_failed_str = previous.get("failed_tests", "")
            prev_failed_set = {t.strip() for t in prev_failed_str.split(",") if t.strip()} if prev_failed_str else set()
            new_failures = [t for t in _results["failed"] if t not in prev_failed_set]
            if new_failures:
                for nf in new_failures:
                    tw.write_line(f"    NEW FAIL: {nf}", red=True)
        elif df < 0:
            tw.write_line(f"  failed:  {failed} ({df}, improved!)", green=True)
        else:
            tw.write_line(f"  failed:  {failed} (unchanged)")

        # skipped
        ds = skipped - prev_s
        if ds > 0:
            tw.write_line(
                f"  WARNING: {ds} new skip(s)  (was {prev_s}, now {skipped})",
                yellow=True, bold=True,
            )
        elif ds < 0:
            tw.write_line(f"  skipped: {skipped} ({ds})")
        else:
            tw.write_line(f"  skipped: {skipped} (unchanged)")

        tw.write_line(f"  duration: {duration:.1f}s | e2e: {'included' if _e2e_included else 'excluded'}")
        tw.write_line(f"  saved to {_LAST_RUN}")
    else:
        tw.section("Test Log (first run)")
        tw.write_line(f"  {passed} passed, {failed} failed, {skipped} skipped")
        tw.write_line(f"  saved to {_LAST_RUN}")
