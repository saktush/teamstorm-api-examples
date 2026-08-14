# Real API smoke-test runbook

## Preconditions

- Install a pinned Git commit in an isolated environment.
- Obtain API URL and token from the active harness without printing either secret.
- Use a unique UTC-based workspace key and name.
- Never use `allow_insecure=True` with real credentials.

## Sequence

1. Harmless authenticated read such as `api.workspaces.list()`. Stop on 401/403 before mutation.
2. Create and read a dedicated workspace.
3. Create root and nested folders; list them.
4. Create a Tag attribute, Agile configuration, and sprint.
5. Discover an existing type/workflow; create parent and child workitems, patch and read back.
6. Add/list a comment and link when supported.
7. Create portfolio and element; link once, then read back even if response validation fails.
8. Create document, comment, workitem link, and a tiny deterministic attachment.
9. Read back every created object from a new process.

Do not blindly retry creates, comments, links, or uploads. Do not delete the workspace unless cleanup is explicitly requested.

## Report contract

Record the Git commit, sanitized host, UTC start/end, workspace key/ID, PASS/FAIL/SKIP per step, created IDs, artifact paths, redacted errors, whether mutations occurred, and the next action. Authentication failure before mutation is **BLOCKED**, not a wrapper failure.
