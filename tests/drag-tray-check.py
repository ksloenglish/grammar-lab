"""Revised tap-only regression: native/synthetic drag must NOT change answers.

Retains the historical filename so existing verification commands remain useful.
Run with GRAMMAR_TEST_URL set to a ready local or live server. The shared focused
suite checks fresh Chromium/WebKit contexts and saves results under the ignored
test-results/tap-only-ui/ directory.
"""
import importlib.util
from pathlib import Path

path = Path(__file__).with_name("tap-only-ui-check.py")
spec = importlib.util.spec_from_file_location("tap_only_ui_check", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if __name__ == "__main__":
    module.run_drag_regression()
