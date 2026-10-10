### 2.0.0 / Unreleased ###
* **Breaking Change**: Python 3.9, 3.10, and 3.11 are no longer supported. Installing 2.0 requires Python 3.12 or newer; upgrade the interpreter before upgrading the SDK. Applications that must stay on those older interpreters can pin `pytransloadit<2` (the latest 1.x release is 1.0.4).
* **Breaking Change**: Runtime dependencies now require `requests>=2.33,<3` and `urllib3>=2.7,<3`. Remove or update older pins in application requirements/constraints and regenerate the application lockfile; incompatible pins will prevent installation.
* The synchronous client API, imports, Assembly creation/polling, uploads, and Smart CDN signing remain compatible with 1.0.4 on supported interpreters.
* Added all 44 documented API operations to both sync and async clients: Assemblies, Assembly Notifications, Templates, Template Credentials, auth keys and token grants, DAM, statistics, Priority Job Slots, Billing, SSE and raw TUS. DAM operations marked alpha retain that status. The 16 separate-product storage/device/OAuth routes are tracked for 2.1 in #60.
* Pinned the canonical API2 contract with producer revision and byte hash. Low-level methods and the coverage table regenerate deterministically; CI checks the committed bytes without API2 access. High-level Assembly, Template and upload helpers remain handwritten.
* Added signed PATCH, multipart PUT Assembly replacement, optional bearer-token authentication and authorization-code/refresh-token issuance. SSE supports incremental events and context-managed cancellation/cleanup. Raw TUS preserves binary downloads and response headers, validates returned destinations and does not forward account credentials or follow redirects.
* Added explicit asyncio support with `AsyncTransloadit`, async request/assembly/template helpers, and `asyncio.sleep`-based polling. Resumable uploads stay on the existing TUS client, but run through `asyncio.to_thread()` so the event loop remains responsive instead of pretending the sync uploader is natively async.
* Async cancellation drains active multipart reads and resumable workers, including repeated cancellation, before releasing caller-owned files. Isolated public, token, SSE and raw TUS transports preserve proxy/TLS configuration without borrowing session or netrc account credentials. High-level TUS helpers validate metadata and preserve Assembly creation errors.
* Explicit bearer authentication wins over ambient netrc or session auth. Assembly capability requests isolate account credentials while preserving custom deployment worker hosts. Async multipart uploads retain text-mode file support, and polling continues through `ASSEMBLY_REPLAYING`.
* Hardened upload and response edge cases: invalid service URLs and empty template IDs now fail fast, external absolute API URLs are no longer signed, sync TUS uploads now handle nameless streams and submit rate limits before uploading, sync non-resumable retries rewind seekable files and reject non-seekable retry streams, sync/async polling rate-limit retries reset after successful polls and cap repeated rate limits, async form fields match sync boolean serialization, async TUS cancellation waits for worker cleanup, async rate-limit backoff honors server `retryIn`, Smart CDN signing rejects invalid workspace slugs/reserved query keys, and sync non-JSON responses fall back to response text.
* Hardened sync and async request handling by preserving custom `auth` constraints, quoting path IDs, and keeping explicit/custom service URLs compatible with local, CI, and [Transloadit Gateway](https://github.com/transloadit/gateway) deployments.
* Fixed sync and async template creation to send the current API `template` payload shape.
* The dependency refresh already released in 1.0.4 remains available to 1.x users; 2.0 removes the old-interpreter lockfile variants and requires the newer HTTP stack on every supported runtime.
* Updated development and documentation tooling, including `pytest` 9.0.3, `Sphinx` 9.1, `sphinx-autobuild` 2025.8, `coverage` 7.14, `tox` 4.54, and `requests-mock` 1.12.
* Updated CI and local Docker test coverage to a representative Python 3.12, 3.13, and 3.14 matrix.
* Migrated package metadata to the modern `[project]` format used by Poetry 2.
* Source contributors need Poetry 2.4.1 for the documented Docker/CI toolchain; isolated package builds require `poetry-core>=2.2,<3`. Normal `pip` installation installs the build backend automatically when needed.
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
