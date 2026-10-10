# Python 2.0 API coverage

Python 2.0 implements all **44 documented operations** in both `Transloadit` and
`AsyncTransloadit`: 38 API2 endpoints and six raw TUS operations. Async ordinary
methods are awaited; `stream_assembly_status` returns an async context manager.
Assembly, Template, polling and tuspy upload helpers remain maintained by hand.

The initial async draft reached 22 of 38 API2 operations, including a POST alias
for Assembly replacement and partial token issuance. The new methods add auth-key
management, DAM, statistics, canonical multipart replacement, SSE and raw TUS.

## Reproducible generation

`contracts/api2-contract.lock.json` records the producer revision and SHA-256 of
the original contract bytes. `contracts/api2-contract.json.gz` contains those
unmodified bytes compressed with a fixed timestamp. The pin is API2 main
`27622f3ecd09ffef6fc86a43dcfe14b95deaaad6`, published from
`api2/generated/contracts/v1/contract.json`. The SDK build does not require API2
credentials or a network request.

```bash
python scripts/generate_endpoints.py
python scripts/generate_endpoints.py --check
# Update only from a reviewed, committed API2 revision:
python scripts/generate_endpoints.py --api2-root ../api2 --ref <commit>
```

The generator consumes `apiReference.operations` and the corresponding dispatch
and exchange records. It derives HTTP paths/methods, transport kinds, stages,
token-grant authentication, protocol header defaults and SSE terminal events.
Python compatibility names are the only SDK-specific method-name overrides.
CI checks both client blocks, transport metadata and this table byte for byte.
The 102 public dispatch entries include guards, aliases, routing and separate
products; they are not 102 SDK endpoint methods. OpenAPI is a served projection
of the canonical contract, not a checked-in `openapi.json` file in this pin.

## Documented operations

Methods accept normalized request fields as a `params` dictionary for GET or
`data` for other ordinary methods. Pass files/extra fields to Assembly creation
and replacement. Response payloads remain dictionaries rather than generated
model classes. The server validates request fields. A covered operation does not
mean that every response or server-side permission has a live test in this repo.

<!-- generated-coverage -->
| Operation | HTTP request | Sync / async method | Stage |
| --- | --- | --- | --- |
| `api2.assembly-stats` | `GET /assembly_stats` | `assembly_stats` |  |
| `api2.bulk-delete-dam-assets` | `POST /dam/assets/bulk/delete` | `bulk_delete_dam_assets` | alpha |
| `api2.bulk-move-dam-assets` | `POST /dam/assets/bulk/move` | `bulk_move_dam_assets` | alpha |
| `api2.cancel-assembly` | `DELETE /assemblies/{assemblyId}` | `cancel_assembly` |  |
| `api2.create-assembly` | `POST /assemblies` | `create_assembly` |  |
| `api2.create-auth-key` | `POST /auth_keys` | `create_auth_key` |  |
| `api2.create-template` | `POST /templates` | `create_template` |  |
| `api2.create-template-credential` | `POST /template_credentials` | `create_template_credentials` |  |
| `api2.delete-auth-key` | `DELETE /auth_keys/{authKeyId}` | `delete_auth_key` |  |
| `api2.delete-dam-asset` | `DELETE /dam/assets/{assetId}` | `delete_dam_asset` | alpha |
| `api2.delete-template` | `DELETE /templates/{templateIdOrName}` | `delete_template` |  |
| `api2.delete-template-credential` | `DELETE /template_credentials/{templateCredentialId}` | `delete_template_credentials` |  |
| `api2.get-assembly` | `GET /assemblies/{assemblyId}` | `get_assembly` |  |
| `api2.get-bill` | `GET /bill/{billYearMonth}` | `get_bill` |  |
| `api2.get-dam-asset` | `GET /dam/assets/{assetId}` | `get_dam_asset` |  |
| `api2.get-template` | `GET /templates/{templateIdOrName}` | `get_template` |  |
| `api2.get-template-credential` | `GET /template_credentials/{templateCredentialId}` | `get_template_credentials` |  |
| `api2.issue-bearer-token` | `POST /token` | `issue_bearer_token` |  |
| `api2.list-assemblies` | `GET /assemblies` | `list_assemblies` |  |
| `api2.list-assembly-notifications` | `GET /assembly_notifications/{assemblyId}` | `list_assembly_notifications` |  |
| `api2.list-auth-key-scopes` | `GET /auth_keys/scopes` | `list_auth_key_scopes` |  |
| `api2.list-auth-keys` | `GET /auth_keys` | `list_auth_keys` |  |
| `api2.list-dam-assets` | `GET /dam/assets` | `list_dam_assets` |  |
| `api2.list-priority-job-slots` | `GET /queues/job_slots` | `list_priority_job_slots` |  |
| `api2.list-template-credential-types` | `GET /template_credentials/types` | `list_template_credential_types` |  |
| `api2.list-template-credentials` | `GET /template_credentials` | `list_template_credentials` |  |
| `api2.list-templates` | `GET /templates` | `list_templates` |  |
| `api2.move-dam-asset` | `PATCH /dam/assets/{assetId}` | `move_dam_asset` | alpha |
| `api2.move-dam-entry` | `POST /dam/entries/move` | `move_dam_entry` | alpha |
| `api2.priority-job-slot-stats` | `GET /priority_job_slot_stats` | `priority_job_slot_stats` |  |
| `api2.replace-assembly` | `PUT /assemblies/{assemblyId}` | `replace_assembly` |  |
| `api2.replay-assembly` | `POST /assemblies/{assemblyId}/replay` | `replay_assembly` |  |
| `api2.replay-assembly-notification` | `POST /assembly_notifications/{assemblyId}/replay` | `replay_assembly_notification` |  |
| `api2.show-auth-key-secret` | `POST /auth_keys/show_secret/{authKeyId}` | `show_auth_key_secret` |  |
| `api2.stream-assembly-status` | `GET /{statusStream}` | `stream_assembly_status` |  |
| `api2.update-auth-key` | `PUT /auth_keys/{authKeyId}` | `update_auth_key` |  |
| `api2.update-template` | `PUT /templates/{templateIdOrName}` | `update_template` |  |
| `api2.update-template-credential` | `PUT /template_credentials/{templateCredentialId}` | `update_template_credentials` |  |
| `tusd.create-upload` | `POST /resumable/files` | `create_upload` |  |
| `tusd.delete-upload` | `DELETE /resumable/files/{uploadId}` | `delete_upload` |  |
| `tusd.download-upload` | `GET /resumable/files/{uploadId}` | `download_upload` |  |
| `tusd.get-upload-offset` | `HEAD /resumable/files/{uploadId}` | `get_upload_offset` |  |
| `tusd.options` | `OPTIONS /resumable/files` | `tus_options` |  |
| `tusd.patch-upload` | `PATCH /resumable/files/{uploadId}` | `patch_upload` |  |
<!-- /generated-coverage -->

## Compatibility and 2.1 boundary

The five staged DAM operations retain their producer's alpha designation.
`create_assembly_with_id` remains the accepted POST replacement alias;
`replace_assembly` uses canonical PUT. Builtin Template and invoice helpers are
variants of existing public operations, not additional operation IDs.

The inherited `get_template_full`, `get_builtin_template_full` and
`validate_template_credential_oauth_on_create` helpers remain for compatibility
with the draft. API2 now classifies these Console routes as internal: they are
excluded from public-contract generation and the table above. Use the documented
Template and Template Credential APIs for new integrations.

The 16 storage-management, device-authorization, OAuth and self-revocation routes
marked `separate-product-surface` are deferred to
[Python 2.1 issue #60](https://github.com/transloadit/python-sdk/issues/60).
Delegated S3/MCP/Companion/Socket.IO protocols, dispatch guards and operational
recovery routes are outside this SDK endpoint surface.
