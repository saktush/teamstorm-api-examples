# TeamStorm CWM Public API — operational semantics

This document records behavior relevant to callers of the TeamStorm CWM Public API. Its public sources of truth are:

- the committed OpenAPI snapshot [`../openapi/swagger-v4.18.0.json`](../openapi/swagger-v4.18.0.json);
- the typed request/response models and resource wrappers in this repository;
- responses observed on the TeamStorm deployment you operate against.

Deployments and API versions can differ. Treat notes not represented by the OpenAPI contract as operational guidance, not a compatibility guarantee. Confirm destructive operations, limits, authorization behavior, and retry assumptions on a non-production environment before automating writes.

## 1. Authentication

`TsClient` sends the token as:

```http
Authorization: PrivateToken <token>
```

Pass only the bare token to `TsClient`; it adds the `PrivateToken ` prefix. Do not print headers or tokens. HTTPS is required by default. `allow_insecure=True` is intended only for local mock servers without real credentials.

Some deployments also accept a `Timezone` request header for date-bucketed queries. Treat it as deployment-dependent unless it appears in the current API contract.

## 2. Pagination

Pagination is not universal. Cursor-paginated resources use an envelope shaped like:

```json
{
  "fromToken": null,
  "maxItemsCount": 50,
  "nextToken": "opaque-or-null",
  "items": []
}
```

Continue while `nextToken` is not `null`, passing it back as `fromToken`. Treat tokens as opaque strings. The checked contract permits `maxItemsCount` values from 1 through 1000 on endpoints that expose this parameter.

Most high-level `list()` wrappers collect all pages. For large datasets, prefer `TsClient.iter_all()` and validate each item with its response model. Several workspace-configuration list endpoints return a bare array and do not accept cursor parameters; check each resource signature instead of assuming a global pagination shape.

No general sort parameter is present in the checked OpenAPI snapshot. Do not depend on server ordering unless a specific endpoint documents it.

## 3. JSON names, enums, and models

Request models accept Python `snake_case` field names and serialize their aliases for the wire. Construct typed request models rather than arbitrary dictionaries:

```python
payload = body.model_dump(mode="json", exclude_none=True)
```

Enum values are transmitted using their string values. Import and use the enums under `teamstorm.models` rather than guessing localized labels or integer ordinals.

Unknown fields are rejected by the strict models. This makes API drift visible instead of silently discarding input.

## 4. Partial updates and explicit `None`

True partial-update bodies distinguish:

- an omitted field — leave the remote value unchanged;
- an explicitly supplied `None` — send JSON `null` and clear the value where supported.

The wrappers therefore use:

```python
body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
```

for partial-merge operations. Single-field rename/update endpoints may require their field and do not necessarily share partial-merge semantics. `WorkitemsAPI.update_attribute` also preserves a required nullable `value`, because JSON `null` is used to clear an attribute.

See [`conventions.md`](conventions.md) and [`../technical-behavior.md`](../technical-behavior.md) for the serialization rules implemented by the wrappers.

## 5. Workitem links

Creating a workitem link requires:

- `type` — link type ID or accepted name;
- `linkedWorkspace` — key or ID of the target workspace;
- `linkedWorkitem` — key or ID of the target workitem.

Use `CreateWorkitemLinkRequestBody`:

```python
from teamstorm.models.links import CreateWorkitemLinkRequestBody

body = CreateWorkitemLinkRequestBody(
    type="RELATES",
    linked_workspace="TARGET_SPACE",
    linked_workitem="TS-42",
)
```

A duplicate or invalid link may be rejected. Read existing links before retrying a failed create operation.

## 6. Attachments

Use the typed attachment resources rather than constructing paths manually. The public contract exposes workitem and document operations for listing metadata, uploading, downloading, deleting attachments, and reading/deleting versions.

Operational precautions:

- upload with the exact multipart field expected by the current wrapper;
- stream large files instead of loading them fully into memory;
- do not assume a universal maximum file size — deployment policy can differ;
- treat antivirus, extension, signature, or tenant-policy rejections as possible deployment-specific errors;
- do not retry a failed upload blindly: read attachment state first, because the server may have persisted data before the client observed a complete response;
- verify multi-version upload behavior on the target deployment before depending on it.

## 7. Error handling

`TsClient` raises `ApiError` for transport failures and non-success responses. Preserve the HTTP method, path, status, and sanitized response information in diagnostics; redact authorization headers, tokens, sensitive request bodies, and secret-bearing URLs.

Common classes of responses include:

- `400` — invalid model or business rule;
- `401` — authentication challenge failed;
- `403` — authenticated caller lacks permission;
- `404` — resource not found;
- `409` — conflict on operations that define it;
- `413` — request or upload exceeds an enforced limit;
- `423` — resource temporarily locked, for example by file policy;
- `429` — possible infrastructure-level throttling even when not described by the OpenAPI snapshot;
- `5xx` — server or downstream failure.

Some deployments use `402 Payment Required` for unavailable license features. Treat that as a recoverable deployment/license condition rather than an authentication failure.

Error payloads can contain `type`, `key`, `messages`, and `payload`, but callers must tolerate non-JSON proxy responses as well.

## 8. Retry and idempotency

Do not assume create operations are idempotent. A repeated `POST` can create a second entity. Automatic retries should normally be limited to safe reads unless the workflow has a stable external key and performs a read-back before retrying.

For any timeout or response-validation failure after a write:

1. stop;
2. query the relevant resource using a stable identifier;
3. decide whether the write committed;
4. retry only when duplication is impossible or acceptable.

## 9. Resource-specific cautions

- Parent identifiers can be required by the wrappers even where a permissive wire schema appears to allow omission; this protects the repository's tree-oriented examples.
- Document content is HTML-oriented. Do not assume byte-for-byte round trips for plain text formatting.
- Treat delete operations as irreversible unless the current deployment explicitly documents a restore path.
- Persist secret values returned only during create/refresh operations; later list/get responses may intentionally omit them.
- Resolve user-defined statuses, types, link types, and attribute options through their list endpoints rather than hardcoding display names.
- Validate `Tag` and `UniSelect` option names before writes when silent omission would be harmful.
- Time-tracking and query endpoints have resource-specific scopes and capabilities; inspect their signatures and the OpenAPI snapshot instead of inferring CRUD completeness from the tag name.

## 10. Verification before automation

Before using a new resource against production:

1. pin a reviewed Git commit;
2. inspect the exact method signature and request model;
3. compare it with the committed OpenAPI snapshot and the target deployment version;
4. run a harmless authenticated read;
5. test writes in a disposable workspace;
6. read back state after every mutation;
7. document deployment-specific deviations locally without committing credentials or confidential implementation details.
