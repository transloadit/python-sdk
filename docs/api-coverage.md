# Python 2.0 API coverage checkpoint

Measured on 2026-10-10, after merging #56 (`2397ea5`) into #57 (`79bfb19`).
This is a source audit and scope proposal, not a claim that the endpoints have
passed live contract-conformance tests. No new endpoint implementation is included
in this checkpoint.

## Contract and counting rule

- API2 revision: [`27622f3ecd09ffef6fc86a43dcfe14b95deaaad6`](https://github.com/transloadit/api2/commit/27622f3ecd09ffef6fc86a43dcfe14b95deaaad6).
- Source: [`api2/generated/contracts/v1/contract.json`](https://github.com/transloadit/api2/blob/27622f3ecd09ffef6fc86a43dcfe14b95deaaad6/api2/generated/contracts/v1/contract.json).
- SHA-256 of the committed contract bytes: `59c41853f194b01b6560f57a696afba89d774281d32f80d9ed03de724895a2a8`.
- Use `apiReference.operations` for the documented SDK surface: **44 operations**,
  comprising **38 API2 operations and 6 raw TUS operations**.
- `contract.operations` contains **102 dispatch operations**. These also describe
  edge routing, guards, method tunnels, aliases, fallbacks and separate products;
  they are not 102 distinct SDK methods.
- Another **16 ordinary API routes** explicitly have
  `apiReference.reason = separate-product-surface`. They are listed below rather
  than silently counted as documented API-reference endpoints.
- At this revision `openapi.json` is a served projection, not a checked-in file at
  `api2/generated/contracts/v1/openapi.json`. The canonical contract is the source
  of this inventory. The old API2 SDK generator/example test commands mentioned
  in #57 are absent from current API2 main.

The sync and async clients have matching endpoint reachability: **22 of 38 API2
operation IDs** have a callable path. Of these, 21 have the canonical HTTP method
and path; token issuance supports only one grant. The 22nd is replace-Assembly,
reachable via its accepted POST alias. **16 API2 operations have no wrapper**:
6 auth-key operations, 7 DAM operations, 2 statistics operations and the status
stream. TUS create/offset/PATCH are exercised through upload/resume workflows;
OPTIONS, download and delete are missing. None of the six has a standalone
low-level TUS endpoint method.

Reachability does not certify every request field, auth alternative or response
mode. In particular, bearer-authenticated API requests and the token endpoint's
other grants are not implemented by the general request transports.

## Sync and async coverage

Each method below exists in both `Transloadit` and `AsyncTransloadit`; async calls
are awaited. The request/response helpers in `assembly.py`, `async_assembly.py`,
`template.py` and `async_template.py` remain separate high-level APIs.

| Contract operation | Canonical request | Current sync and async coverage |
| --- | --- | --- |
| `api2.assembly-stats` | `GET /assembly_stats` | Missing |
| `api2.bulk-delete-dam-assets` | `POST /dam/assets/bulk/delete` | Missing |
| `api2.bulk-move-dam-assets` | `POST /dam/assets/bulk/move` | Missing |
| `api2.cancel-assembly` | `DELETE /assemblies/{assemblyId}` | `cancel_assembly` |
| `api2.create-assembly` | `POST /assemblies` | `create_assembly` |
| `api2.create-auth-key` | `POST /auth_keys` | Missing |
| `api2.create-template` | `POST /templates` | `create_template` |
| `api2.create-template-credential` | `POST /template_credentials` | `create_template_credentials` |
| `api2.delete-auth-key` | `DELETE /auth_keys/{authKeyId}` | Missing |
| `api2.delete-dam-asset` | `DELETE /dam/assets/{assetId}` | Missing |
| `api2.delete-template` | `DELETE /templates/{templateIdOrName}` | `delete_template` |
| `api2.delete-template-credential` | `DELETE /template_credentials/{templateCredentialId}` | `delete_template_credentials` |
| `api2.get-assembly` | `GET /assemblies/{assemblyId}` | `get_assembly` |
| `api2.get-bill` | `GET /bill/{billYearMonth}` | `get_bill` |
| `api2.get-dam-asset` | `GET /dam/assets/{assetId}` | Missing |
| `api2.get-template` | `GET /templates/{templateIdOrName}` | `get_template` |
| `api2.get-template-credential` | `GET /template_credentials/{templateCredentialId}` | `get_template_credentials` |
| `api2.issue-bearer-token` | `POST /token` | `issue_bearer_token` — client-credentials grant only |
| `api2.list-assemblies` | `GET /assemblies` | `list_assemblies` |
| `api2.list-assembly-notifications` | `GET /assembly_notifications/{assemblyId}` | `list_assembly_notifications` |
| `api2.list-auth-key-scopes` | `GET /auth_keys/scopes` | Missing |
| `api2.list-auth-keys` | `GET /auth_keys` | Missing |
| `api2.list-dam-assets` | `GET /dam/assets` | Missing |
| `api2.list-priority-job-slots` | `GET /queues/job_slots` | `list_priority_job_slots` |
| `api2.list-template-credential-types` | `GET /template_credentials/types` | `list_template_credential_types` |
| `api2.list-template-credentials` | `GET /template_credentials` | `list_template_credentials` |
| `api2.list-templates` | `GET /templates` | `list_templates` |
| `api2.move-dam-asset` | `PATCH /dam/assets/{assetId}` | Missing |
| `api2.move-dam-entry` | `POST /dam/entries/move` | Missing |
| `api2.priority-job-slot-stats` | `GET /priority_job_slot_stats` | Missing |
| `api2.replace-assembly` | `PUT /assemblies/{assemblyId}` | `create_assembly_with_id` — accepted POST alias; no canonical PUT wrapper |
| `api2.replay-assembly` | `POST /assemblies/{assemblyId}/replay` | `replay_assembly` |
| `api2.replay-assembly-notification` | `POST /assembly_notifications/{assemblyId}/replay` | `replay_assembly_notification` |
| `api2.show-auth-key-secret` | `POST /auth_keys/show_secret/{authKeyId}` | Missing |
| `api2.stream-assembly-status` | `GET /{statusStream}` | Missing |
| `api2.update-auth-key` | `PUT /auth_keys/{authKeyId}` | Missing |
| `api2.update-template` | `PUT /templates/{templateIdOrName}` | `update_template` |
| `api2.update-template-credential` | `PUT /template_credentials/{templateCredentialId}` | `update_template_credentials` |
| `tusd.create-upload` | `POST /resumable/files` | Indirect: `upload_tus_assembly` / resumable Assembly upload |
| `tusd.delete-upload` | `DELETE /resumable/files/{uploadId}` | Missing |
| `tusd.download-upload` | `GET /resumable/files/{uploadId}` | Missing |
| `tusd.get-upload-offset` | `HEAD /resumable/files/{uploadId}` | Indirect: `resume_tus_upload` / tuspy resume |
| `tusd.options` | `OPTIONS /resumable/files` | Missing |
| `tusd.patch-upload` | `PATCH /resumable/files/{uploadId}` | Indirect: upload/resume helpers / tuspy |

## Compatibility and transport work

- Add a canonical multipart PUT operation for replacing an Assembly; retain the
  accepted POST helper as a compatibility alias. Both request helpers currently
  accept files only on POST, so this is more than renaming the method.
- Add signed PATCH support for DAM. Preserve the producer's alpha stage on the
  five staged DAM operations; do not describe them as stable.
- `issue_bearer_token` always selects `client_credentials`, forwards only `aud`
  and `scope`, and requires an Auth Secret. The current contract also supports
  authorization-code and refresh-token grants with different authentication.
  Derive grant handling from `auth.byFormField`, not a second SDK grant inventory.
- The generic transports currently sign same-service requests and buffer their
  bodies. SSE needs a separate streaming interface with incremental parsing,
  bounded lifecycle/cancellation and response cleanup for both client types.
- Raw TUS requires response headers, binary bodies, capability destinations and
  upload-resource lifecycle handling. Existing helpers cover normal upload and
  resume, but do not constitute six complete raw endpoint wrappers.
- `get_builtin_template` and `get_bill_for_invoice` are variants of existing
  published operations, not additional operation IDs.
- `get_template_full`, `get_builtin_template_full` and
  `validate_template_credential_oauth_on_create` target routes now explicitly
  marked internal in API2's dispatch registry. Do not regenerate or advertise
  them as public endpoints. Their disposition must be documented when replacing
  the obsolete generated blocks.

## Separate product surface

These 16 routes are present in the public dispatch contract, but API2 deliberately
excludes them from the main API-reference surface. Neither client has dedicated
methods for them.

- `api2.storage-grants-create`
- `api2.storage-public-prefixes-list`
- `api2.storage-public-prefixes-declare`
- `api2.storage-public-prefixes-revoke`
- `api2.cli-device-authorizations-create`
- `api2.cli-device-authorizations-approve`
- `api2.cli-device-authorizations-deny`
- `api2.cli-device-authorizations-token`
- `api2.cli-device-authorizations-find`
- `api2.oauth-client-register`
- `api2.oauth-authorize-context`
- `api2.oauth-authorization-codes-create`
- `api2.oauth-revoke`
- `api2.oauth-connections-list`
- `api2.oauth-connection-revoke`
- `api2.revoke-own-auth-key`

This list does not include delegated Companion/MCP, S3-compatible storage,
Socket.IO, public-platform discovery/fallbacks, operational recovery or dispatch
guards. Those are not ordinary low-level Transloadit endpoint methods.

## Proposed release boundary — requires a decision

**Option A: all documented operations in 2.0 (recommended).** Finish async plus
all **44 documented operations** in both clients, including SSE and all six raw
TUS operations. Keep handwritten Assembly, Template and upload/tuspy helpers.
Generate the low-level surface locally from a pinned API2 contract snapshot with
recorded producer revision/hash, deterministic bytes and an offline `--check`
in CI. Test the new authentication, multipart, PATCH, streaming and capability
boundaries. **2.1** adds the 16 separate-product routes after their storage,
device-authorization and OAuth flows have been designed and tested. Delegated
S3/MCP/Companion/Socket.IO protocols remain with their dedicated clients.

**Option B: smaller 2.0, protocols in 2.1.** Ship async plus all **37 documented
non-streaming API2 operations**, retaining existing resumable upload/resume
helpers. Use the same pinned generation/check and update token grant handling.
**2.1** adds SSE, the standalone raw TUS surface (including currently missing
OPTIONS/download/delete), and the 16 separate-product routes. This is an explicit
reduction of the original full-surface requirement, so the release notes must
state the boundary.

**Option C: include the additional product APIs in 2.0.** Implement the 44
documented operations plus the 16 separate-product API routes before release.
This requires designing and testing OAuth connection, device-authorization and
storage-management flows too. It is a materially larger project than completing
the existing async draft.

No option has been selected. The scope checkpoint occurs before implementing new
endpoint families. Council rounds, full final checks, live devdock scenarios,
CI validation and marking #57 ready with `tim-kos` follow the scope decision.

## Checkpoint validation

- Merged the current #56 branch, which already contains current SDK main, into
  `asyncio-v2`; retained #56 as the PR base.
- Resolved the changelog conflict with the 2.0 `Unreleased` heading and current
  migration requirements. README and Sphinx upgrade notes now include async in
  2.0 rather than contradicting the async examples.
- Python 3.12 Docker unit/example checks: **112 passed, 12 opt-in live skips**;
  coverage **80.38%** (required floor: 65%).
- `git diff --check` passes. No publication, tagging or merge into main occurred.
