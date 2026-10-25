# Recovery follow-up, 2026-10-25

Scope: the three recovery blockers reported against main `7b6e470`, plus the related scene-command deadline mismatch. This correction adds no capability mechanisms and does not qualify arbitrary artist scenes.

## Confirmed defects and corrections

| Defect | Correction | Regression evidence |
| --- | --- | --- |
| Reject revalidates an invalid candidate and leaves the edit pending | Reject uses the accepted checkpoint unless a previous publication already froze its candidate check; atomically retain selected paths/hashes before the check; candidate files remain untouched | Invalid observation cannot be accepted, can be rejected, and a subsequent edit publishes; frozen-check rejection and interrupted rejection in both backends remain supported |
| Recovery records an attempted mutation before the handshake succeeds | Stage attempt identity files and publish them only after handshake and socket connection, immediately before send; persist authenticated stale-generation and read-only preflight refusals | Failed handshake/connection remains retryable; late reload and preflight error refuse before mutation; uncertain sent recovery remains non-repeatable |
| An oversized response is rejected before bridge outcome retention | Serialize and retain the exact durable result before applying the socket limit | A result above 8 MiB is read from durable evidence with no second native dispatch |
| Scene-scanning commands retain a 10-second execution limit | Use matching 180-second client/server deadlines for scene checks, rebind, submission and acknowledgements | Every paired command's server queue deadline is checked against the client policy; handshake stays at 10 seconds |

The oversized-result defect did not necessarily erase the native recovery receipt: the bridge's request-keyed result was missing, preventing the host from consuming that receipt. Both records remain required.

## Verification

The focused regressions initially reproduced the failures. Independent review identified an additional interrupted-rejection failure: the existence of a check alone could not distinguish a previous candidate publication from a rejection using accepted inputs. The correction records that choice before the check. Twelve new regressions cover the reported defects and that resume path. Completed verification results are retained with delivery evidence.

Maintained verification commands:

```text
python scripts/verify_release.py --out NEW_PORTABLE_OUTPUT
python scripts/qualify_execution.py --blender BLENDER --runtime INSTALLED_RUNTIME --out NEW_EXECUTION_OUTPUT
python scripts/qualify_live_transport.py --blender BLENDER --runtime INSTALLED_RUNTIME --out NEW_TRANSPORT_OUTPUT
```

The native transport fixture uses 32 objects and a texture. Its oversized-result test adds 8 MiB of synthetic padding to a real saved recovery receipt; it does not establish 16,000-object scene performance. An 11-second injected snapshot exercises the longer deadline. It also checks unsuccessful handshake admission, definitive refusal followed by one capture, lost-response recovery without recapture, and reconnection after an owned process dies between publication and acknowledgement. The execution fixture creates an actual unlabeled object, refuses acceptance, interrupts and resumes rejection, and publishes a subsequent edit.

Owned native fixtures use precreated CONFIG, SCRIPTS, DATAFILES and EXTENSIONS directories. They do not use or restore the artist's Blender preferences. The earlier 5.1 preferences incident remains unresolved, per the instruction to leave that file untouched.

## Remaining limits

- A request recorded as sent with no definitive result is still uncertain, including a crash immediately before the socket send. No automatic replay or reinterpretation of legacy ambiguous attempts is introduced.
- Whole-scene validation still refuses node groups and other unsupported scene/dependency classes. The next investment should expand measured node-group support and preservation tests before adding more capability machinery.
- Other reported add-on findings remain open: modifier UI state in effect fingerprints, adapter/provider-call mutation, incomplete declared dependencies, and self-attributed network review.
- Cancellation-marker consistency and atomic publication of every outcome record are not addressed by this patch. A process-killed write can still leave incomplete evidence.
- Existing projects remain pinned to their runtime; this patch does not add runtime migration or promise automatic repair of already-corrupted evidence.
- The earlier claim that hosted CI had never run was incorrect: [all four jobs passed on main `7b6e470`](https://github.com/cedarconnor/3D_Harness/actions/runs/40042644685). Historical green CI did not cover these new counterexamples.
