# Contributing

## Releasing

**Prerequisites**
- Docker installed (our helper scripts build and publish inside the project image)
- Push access to `transloadit/python-sdk`
- PyPI API token with publish rights (`PYPI_TOKEN`), exported or stored in `.env`

**Steps for version `1.0.3` (example)**
1. Bump version in `pyproject.toml`, `transloadit/__init__.py`, and `tests/test_request.py`.
2. Add the `### 1.0.3 / YYYY-MM-DD ###` entry to `CHANGELOG.md`.
3. Run the matrix (add `PYTHON_SDK_E2E=1` if you want the live upload):
   ```bash
   ./scripts/test-in-docker.sh --python 3.12
   ```
4. Commit on `main`: `git commit -am "Prepare 1.0.3 release"`
5. Tag & push:
   ```bash
   git tag v1.0.3
   git push origin main --tags
   ```
6. Publish to PyPI via Docker helper (ensures clean tree & version alignment):
   ```bash
   PYPI_TOKEN=... ./scripts/notify-registry.sh
   ```
7. Publish the GitHub release (pulls notes from the changelog section):
   ```bash
   gh release create v1.0.3 \
     --title "v1.0.3" \
     --notes "$(ruby -e 'puts File.read(\"CHANGELOG.md\")[/^### 1\\.0\\.3/..(/^### / || -1)]')"
   ```
8. Verify the Read the Docs build kicked off: <https://transloadit.readthedocs.io/en/latest/>

Additional background lives here: <https://github.com/transloadit/team-internals/blob/HEAD/_howtos/2020-12-14-maintain-python-sdk.md>.
