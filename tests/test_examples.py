import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPO_ROOT / "examples"
QUICKSTART_EXAMPLES = [
    "image_resize.py",
    "async_image_resize.py",
    "resumable_upload.py",
    "assembly_with_template.py",
    "template_lifecycle.py",
    "smart_cdn_url.py",
]


def _is_e2e_enabled():
    flag = os.getenv("PYTHON_SDK_E2E", "")
    return flag.lower() in {"1", "true", "yes", "on"}


def _has_credentials():
    return bool(os.getenv("TRANSLOADIT_KEY") and os.getenv("TRANSLOADIT_SECRET"))


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


@pytest.mark.e2e
@pytest.mark.skipif(not _is_e2e_enabled(), reason="Set PYTHON_SDK_E2E=1 to run live examples")
@pytest.mark.skipif(
    not _has_credentials(),
    reason="TRANSLOADIT_KEY and TRANSLOADIT_SECRET must be set to run live examples",
)
@pytest.mark.parametrize("example_name", QUICKSTART_EXAMPLES)
def test_quickstart_example_runs_against_transloadit(example_name):
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
    }
    result = subprocess.run(
        [sys.executable, f"examples/{example_name}"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, (
        f"{example_name} failed with exit code {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert result.stdout.strip(), f"{example_name} completed without printing output"
