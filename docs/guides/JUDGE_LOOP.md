# Judge loop

Version 0.25.0, build-plan item G6. A judge loop improves a result toward a stated look over a bounded number of attempts. It is a folder of append-only records and four commands. It launches nothing: the calling agent builds each candidate, hands a packet to a fresh-context judge, and records the answer. The record then says what happens next.

```powershell
python -m dcc_harness judge-start "<work>/loop" --target "<work>/target.json"
python -m dcc_harness judge-round "<work>/loop" --evidence "<work>/round1/evidence.json"
python -m dcc_harness judge-verdict "<work>/loop" --verdict "<work>/round1/verdict.json"
python -m dcc_harness judge-status "<work>/loop"
```

A judge score is an agent's opinion. Every result says so, and it never stands for owner acceptance.

## Target first

`judge-start` fixes the target before anything is built. The loop folder must be new.

```json
{"schema": "dcc.judge.target.v1",
 "brief": "A handmade three-legged milking stool with a terracotta pot on it, on worn stone paving, in low warm sun.",
 "targets": [{"id": "handmade-timber", "intent": "The stool reads as hand-made timber with visible grain."}],
 "references": [{"id": "mood", "role": "mood", "intent": "Low warm light", "file": {"path": "refs/mood.png"}}],
 "spec": {"path": "spec.json"},
 "pass_score": 9}
```

- **`targets`** are the visual targets the judge scores against. At least one.
- **`references`** are optional images, each with a role of `target`, `mood`, `construction` or `dimension`. Their hashes are recorded. A generated target image goes here with role `target`, when the owner asks for one.
- **`spec`** is an optional [blockout spec](BLOCKOUT_SPEC.md). With it, every round needs a passing `spec-compare`.
- **`pass_score`** is the total at which the loop stops as met. The default is 9 of 10.

## A round

Build one candidate, save it as a new file, and run the code checks on that file. Then describe the round:

```json
{"schema": "dcc.judge.evidence.v1",
 "approach": "Procedural grain along each part; edge-wear mask on the seat.",
 "checkpoint": {"path": "candidate.blend"},
 "audit": {"path": "audit/report.json"},
 "spec_compare": {"path": "compare/report.json"},
 "views": {"path": "views/receipt.json"},
 "sheet": {"path": "sheet/receipt.json"}}
```

`judge-round` verifies that every report and receipt was made for that exact file and that the images are unchanged since their receipts.

**Code checks come first.** If the [`audit`](AUDIT.md) report has an error, or `spec-compare` has a finding, the round is recorded as `gated`. It gets no judge packet, the command exits 1, and it still uses one of the five rounds. A judge names symptoms well and causes badly, so defects that code can measure are never left for it to find.

A round that passes gets a packet in `packets/`: the brief, the targets, the reference images, the round's fixed views and [review sheet](REVIEW_SHEET.md), the rubric, and the previous verdict.

## The judge

Give the packet to a separate agent with a fresh context. It should see nothing about how the result was built. It scores the rubric and lists gaps:

| Line | Range |
|---|---|
| Composition | 0 to 3 |
| Lighting | 0 to 3 |
| Materials | 0 to 3 |
| Detail | 0 to 1 |

```json
{"schema": "dcc.judge.verdict.v1", "judge": {"author": "judge agent, round 2", "context": "fresh"},
 "scores": {"composition": 2, "lighting": 2, "materials": 1, "detail": 0},
 "gaps": [{"id": "flat-timber", "where": "hero view, seat and legs", "problem": "one flat brown with no grain"}],
 "summary": "Reads as a stool; materials are placeholders."}
```

- A gap has a lowercase ID, where it is seen and what is wrong. The judge reuses an ID when the same gap remains.
- A score below 10 must name at least one gap.
- `context` is `fresh` for a separate agent and `same` when the builder judged its own work. Say which honestly; the record keeps it.

With `project_checkpoint` in the evidence (`{checkpoint_id, checkpoint_sha256}` of a published checkpoint), `judge-verdict` also writes one feedback-note draft per gap in `notes/`. Each is an advisory visual note attributed to the judge, ready for `feedback-add`.

## What happens next

`judge-verdict` and `judge-status` return `next`:

| `next` | Meaning |
|---|---|
| `build` | No round yet |
| `judge` | The last round passed its checks and waits for a verdict |
| `fix_gates` | The last round failed its checks; repair them |
| `continue` | Address the named gaps |
| `change_approach` | Progress stalled; the next round must take a different approach |
| `stop_target_met` | The score reached `pass_score`. Present it to the owner |
| `stop_ask` | A changed approach also failed. Ask the owner |
| `stop_cap` | All five rounds are used. Ask the owner |

**The stall rule.** A loop has stalled when the judge names the same gap in two consecutive verdicts and the score gained less than one point between them, or when the score has gained less than one point across two rounds. A repeated gap alone is not a stall: a judge that lists many gaps repeats some while the score is still rising. The first stall requires a change of approach: the next round must give a different `approach` and a `changed_approach` sentence saying what changed, or it is refused. If that round gains less than one point, the loop stops and asks. A second stall later also stops and asks.

**The cap.** Five rounds, gated ones included. After a stop, no further round is accepted. A stop is for the owner to resolve; starting a new loop to get around it defeats the record.

## Resuming

`judge-status` is all a new session needs. It returns the brief, the targets, each round's status, approach, score, gap IDs and what the record required after it (`then`), the open gaps in full, and the instruction for the next step.

## Qualification and first run

`scripts/qualify_judge.py` passed from source on Blender 5.1.1 and 5.2.1. With real `audit`, `spec-compare`, `review-sheet` and `render` output, an inside-out candidate and an off-spec candidate are each recorded as gated with no packet; a clean one reaches the judge; scripted verdicts naming the same gap twice with no point gained require a change of approach; a round without one is refused; and a changed approach that gains nothing stops the loop.

The [first run](../studies/JUDGE_LOOP_FIRST_RUN.md) took one held-out brief to a stop in four rounds and passed a sealed resume test. It showed the original stall rule, a repeated gap alone, firing on a round that had gained three points. The owner changed the rule on November 15 to require no gain as well.

## Limits

- **The loop does not check who judged.** `context: "fresh"` is a claim by the caller.
- **A stall is detected from gap IDs and totals.** A judge that renames a gap each round hides a stall until the score rule catches it.
- **The rubric is fixed** at these four lines.
- **It does not publish.** Checkpoints still go through `finish-edit`, and the owner still accepts.
