# External revisions

Read this when someone, usually the artist, saved a deliberate manual or MCP edit outside a reservation. [External revision review](../../../../docs/guides/EXTERNAL_REVISIONS.md) has the exact commands.

1. Prepare a narrow contract, a fresh saved observation, a handoff and decision updates.
2. Run `preview-revision`. It freezes the candidate and reports the changed fields and the users of any shared material.
3. Inspect that frozen copy.
4. Run `accept-revision` with the exact preview hash and a factual review note.
5. Make any further requested change as an ordinary reserved edit on top.

- This route does not repair IDs or settle a pending native operation.
- A changed parent invalidates the preview.
- Observed external dependencies require a self-contained owned copy.
- A lost acknowledgement may return `ALREADY_PUBLISHED`. Do not rebuild or republish the edit.
