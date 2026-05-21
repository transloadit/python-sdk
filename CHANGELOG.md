### 2.0.0 / 2026-05-20 ###
* **Breaking Change**: Raised the supported Python runtime floor from 3.9+ to 3.12+ so the SDK no longer has to retain vulnerable locked dependency versions for EOL Python 3.9 or depend on tooling lines that are already dropping older runtime support.
* Added explicit asyncio support with `AsyncTransloadit`, async request/assembly/template helpers, and `asyncio.sleep`-based polling. Resumable uploads stay on the existing TUS client, but run through `asyncio.to_thread()` so the event loop remains responsive instead of pretending the sync uploader is natively async.
* Hardened upload and response edge cases: invalid service URLs and empty template IDs now fail fast, external absolute API URLs are no longer signed, sync TUS uploads now handle nameless streams and submit rate limits before uploading, async form fields match sync boolean serialization, async TUS cancellation waits for worker cleanup, async polling rate-limit retries reset after successful polls, async rate-limit backoff honors server `retryIn`, Smart CDN signing rejects invalid workspace slugs/reserved query keys, and sync non-JSON responses fall back to response text.
* Hardened sync and async request handling by preserving custom `auth` constraints, quoting path IDs, and keeping explicit/custom service URLs compatible with local, CI, and [Transloadit Gateway](https://github.com/transloadit/gateway) deployments.
* Fixed sync and async template creation to send the current API `template` payload shape.
* Raised the runtime HTTP stack to patched versions by requiring `requests` 2.33+ and adding an explicit `urllib3` 2.7+ floor.
* Updated development and documentation tooling, including `pytest` 9.0.3, `Sphinx` 9.1, `sphinx-autobuild` 2025.8, `coverage` 7.14, `tox` 4.54, and `requests-mock` 1.12.
* Updated CI and local Docker test coverage to a representative Python 3.12, 3.13, and 3.14 matrix.
* Migrated package metadata to the modern `[project]` format used by Poetry 2.
* Refreshed GitHub Actions, release documentation, and Sphinx docs that still referenced older runtime/tooling assumptions.

### 1.0.4 / 2026-05-20 ###
* Refreshed locked runtime and development dependencies, including `aiohttp` 3.13.5, `idna` 3.15, `pygments` 2.20.0, Python-version-specific `requests` updates, and `tuspy` 1.1.0.
* Updated development tooling to Python 3.9-compatible majors: `pytest` 8.4, `pytest-cov` 7.1, `Sphinx` 7.4, and `sphinx-autobuild` 2024.10.
* Kept SDK runtime support at Python 3.9+ to match package metadata, README, and CI, and held back newer tooling majors that require a higher Python floor.
* Removed obsolete compatibility and documentation tooling from the dependency surface, including `six`, `livereload`, and `tornado`.

### 1.0.3/ 2025-28-10 ###
* Added a Docker-based test harness (`scripts/test-in-docker.sh`) that mirrors our GitHub Actions matrix locally, including optional Smart CDN parity checks via the official Transloadit CLI.
* Introduced an opt-in end-to-end image resize test (`tests/test_e2e_upload.py`) plus supporting `chameleon.jpg` fixture; enable by setting `PYTHON_SDK_E2E=1` along with `TRANSLOADIT_KEY`/`TRANSLOADIT_SECRET`.
* Updated CI to run the E2E upload on Python 3.12 with guarded secrets and to skip coverage for that targeted job.
* Documented the new workflows and ensured the Transloadit CLI integration replaces the legacy TypeScript helper.

### 1.0.2/ 2024-03-12 ###
* Add support for Python 3.13

### 1.0.1/ 2024-28-11 ###
* Added SDK support for signed Smart CDN URLs (see https://transloadit.com/docs/topics/signature-authentication/#smart-cdn).
  This is shipped within the new client#get_signed_smart_cdn_url() method.
* Version updates for dependencies.

### 1.0.0/ 2024-16-07 ###

* **Breaking Change**: Python versions prior to 3.9 have been deleted as they are no longer supported.
* Updating packages versions.

### 0.2.2/ 2024-10-04 ###
- Added `sha_384` as hash algorithm for the signature authentication.
- Drop Python 3.6 from CI. It has been unsupported since December 2021 and github actions runner don't support anymore (https://github.com/actions/setup-python/issues/544)

### 0.2.1/ 2022-29-08 ###

* Add documentation on publishing releases
* Avoid creating a new Assembly when a rate limit error is received from fetching an Assembly too frequently

### 0.2.0/ 2022-21-06 ###

* Drop Python versions before 3.7 as they are unsupported
* Update code to Python 3 syntax
* Prevent rate limiting when polling Assembly status

### 0.1.12/ 2020-14-12 ###

* Send `transloadit-client` header along with requests

### 0.1.10/ 2018-27-08 ###

* Drop the use of requirements.txt for dependencies
* Update dependency versions

### 0.1.9/ 2018-12-04 ###

* Loosen request module's version

### 0.1.8/ 2018-19-03 ###

* Update tuspy version
* Increase upload chunk size
