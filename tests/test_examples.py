import os
import runpy
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPO_ROOT / "examples"


def test_examples_import_without_side_effects():
    for example_path in sorted(EXAMPLES_ROOT.glob("*.py")):
        if example_path.name == "__init__.py":
            continue
        runpy.run_path(str(example_path), run_name="__example_import__")


def test_smart_cdn_example_runs_without_network():
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "TRANSLOADIT_KEY": "test-key",
        "TRANSLOADIT_SECRET": "test-secret",
        "TRANSLOADIT_WORKSPACE": "workspace",
        "TRANSLOADIT_TEMPLATE": "template",
        "TRANSLOADIT_INPUT": "image.jpg",
    }
    result = subprocess.run(
        [sys.executable, "examples/smart_cdn_url.py"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.startswith("https://workspace.tlcdn.com/template/image.jpg?")
    assert "sig=sha256%3A" in result.stdout
