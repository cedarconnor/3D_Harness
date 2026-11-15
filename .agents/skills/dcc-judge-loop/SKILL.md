---
name: dcc-judge-loop
description: Use when a Blender result must be improved toward a stated look over several attempts, when asked to iterate until it looks right, when resuming a judge loop folder, or when the same visual fault keeps coming back after repairs.
---

# Judge loop

A judge loop is a folder that records each attempt, its code checks, a fresh judge's score and named gaps, and what must happen next. The record decides the next step; you do not. Full reference: [judge loop guide](../../../docs/guides/JUDGE_LOOP.md).

## Resuming

Run `judge-status LOOP` first and do what `next` says. It carries the brief, every round's score and gaps, and the open gaps. Do not rebuild from memory or re-judge a recorded round.

## The loop

1. **Target first.** Before building, write `target.json`: the brief, the visual targets, any reference images, and a blockout spec when sizes can be stated. `judge-start LOOP --target target.json`. The target is fixed from here.
2. **Build one candidate** and save it as a new file.
3. **Run the code checks on that file:** `audit`, `review-sheet`, `render` with fixed views, and `spec-compare` when the target has a spec.
4. **`judge-round LOOP --evidence evidence.json`.** A round with an audit error or a failed spec-compare is recorded as gated and gets no judge. Repair what the checks name and go again; it used a round.
5. **Hand the printed packet to a fresh-context judge:** a separate agent that sees only the packet's brief, targets, images, rubric and previous verdict. Give it nothing about how you built the result. It answers with one verdict JSON.
6. **`judge-verdict LOOP --verdict verdict.json`**, then follow `next`.

## What `next` means

| `next` | Do |
|---|---|
| `continue` | Address the named gaps, largest first |
| `fix_gates` | Repair the check findings; no judging until they pass |
| `change_approach` | Take a materially different approach and say what changed in `changed_approach`. Tuning the same method is refused |
| `stop_ask`, `stop_cap` | Stop. Show the owner the rounds and ask |
| `stop_target_met` | Stop and present it. This is not acceptance |

## Always

- **The judge names symptoms, not causes.** Find the cause yourself, from the code checks and the file.
- **Never judge your own round as `fresh`.** If no separate agent is available, record `context: "same"`.
- **Never edit a verdict, drop a gap, or start a new loop to escape a stop.** A stop means the owner decides.
- **A judge score is an agent's opinion.** Only the owner accepts work.
- **Keep gap IDs.** The judge reuses an ID when a gap remains; that is how a stall is seen.
