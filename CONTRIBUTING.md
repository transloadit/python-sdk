# Contributing

## Releasing

**Prerequisites**
- Docker installed (our helper scripts build and publish inside the project image)
- Push access to `transloadit/python-sdk`
- PyPI API token with publish rights (`PYPI_TOKEN`), exported or stored in `.env`

**Steps for version `2.0.0` (example)**
1. Bump version in `pyproject.toml`, `transloadit/__init__.py`, and `tests/test_request.py`.
2. Add the `### 2.0.0 / YYYY-MM-DD ###` entry to `CHANGELOG.md`.
3. Run the matrix (add `PYTHON_SDK_E2E=1` if you want the live upload):
   ```bash
   ./scripts/test-in-docker.sh --python 3.14
   ```
4. Commit on `main`: `git commit -am "Release v2.0.0"`
5. Tag & push:
   ```bash
   git tag v2.0.0
   git push origin main --tags
   ```
6. Publish to PyPI via Docker helper (ensures clean tree & version alignment):
   ```bash
   PYPI_TOKEN=... ./scripts/notify-registry.sh
   ```
7. Publish the GitHub release (pulls notes from the changelog section):
   ```bash
   NOTES=$(python3 - <<'PY'
import pathlib, re
version = "2.0.0"
text = pathlib.Path("CHANGELOG.md").read_text()
pattern = rf"^### {re.escape(version)}.*?(?=^### |\Z)"
match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
print(match.group(0).strip() if match else "")
PY
)
   gh release create v2.0.0 --title "v2.0.0" --notes "$NOTES"
   ```
8. Verify the Read the Docs build kicked off: <https://transloadit.readthedocs.io/en/latest/>
9. Verify the published package and the security posture:
   ```bash
   python3 -m pip index versions pytransloadit | head
   gh api repos/transloadit/python-sdk/dependabot/alerts --jq 'map(select(.state == "open")) | length'
   ```

Additional background lives here: <https://github.com/transloadit/team-internals/blob/HEAD/_howtos/2020-12-14-maintain-python-sdk.md>.
