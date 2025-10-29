# Contributing

## Release Checklist

Use this checklist whenever you cut a new version of the Python SDK.

### Prerequisites

- Docker installed (our helper scripts build and run inside the project Docker image).
- Writable Transloadit GitHub repository access.
- A PyPI API token with upload rights to `pytransloadit` (`PYPI_TOKEN`). Store it in your shell or `.env`.
- Optionally, a TestPyPI token (`PYPI_TEST_TOKEN`) if you want to dry‑run the release before pushing to the real registry.

### 1. Prepare the Release Commit

1. Update the version in all synced files:
   - `pyproject.toml`
   - `transloadit/__init__.py`
   - `tests/test_request.py` (the `Transloadit-Client` header)
2. Add a matching entry to `CHANGELOG.md`.
3. Run the test matrix (add `PYTHON_SDK_E2E=1` if you want to exercise the live upload):
   ```bash
   ./scripts/test-in-docker.sh --python 3.12
   ```
4. Commit the changes with a message such as `Prepare 1.0.3 release`.

### 2. Tag the Release

After landing the release commit on `main` (or the branch you will tag), create and push an annotated tag:

```bash
git tag -a v1.0.3 -m "v1.0.3"
git push origin main --tags
```

### 3. Publish to PyPI

The `scripts/notify-registry.sh` helper publishes from inside our Docker image and performs the usual safety checks (clean git tree, version consistency, changelog entry). It looks for tokens in the environment or `.env`.

Publish to the real registry:

```bash
PYPI_TOKEN=... scripts/notify-registry.sh
```

Run a dry‑run against TestPyPI first (optional):

```bash
PYPI_TEST_TOKEN=... scripts/notify-registry.sh --repository test-pypi --dry-run
# When satisfied:
PYPI_TEST_TOKEN=... scripts/notify-registry.sh --repository test-pypi
```

### 4. Announce the Release

1. Draft a GitHub release for the new tag and paste the changelog entry.
2. Confirm that the [Read the Docs build](https://transloadit.readthedocs.io/en/latest/) completes (it is triggered when you publish the GitHub release).

That’s it—PyPI and the documentation are now up to date. For additional background see the internal guide: <https://github.com/transloadit/team-internals/blob/HEAD/_howtos/2020-12-14-maintain-python-sdk.md>.
