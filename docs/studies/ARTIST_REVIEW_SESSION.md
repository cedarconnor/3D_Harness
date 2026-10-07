# Artist review session

Updated October 6, 2026, for build-plan items E1–E3. The whole session now runs in one private review page: [Courtyard and Shed Review](https://claude.ai/artifact/3pWckj3MYMRxfrWzMqHNRJ). It shows one large image at a time, opens any image full screen with zoom to 200%, and saves each answer as you give it, so you can stop and resume on any device.

It takes about 25 minutes, plus an optional 40:

1. **Workflows, 4 screens.** Each anonymous courtyard after four requests in a row. Rate the final result on the original five-point scale, and say whether it stayed true to the shared starting courtyard. A stage selector and a hold-to-compare button show every stage against the start.
2. **Quick picks, 10 screens.** Two versions from the same camera. Flip between them in place, then pick one on a five-step scale from "A clearly" to "B clearly".
3. **Potting shed, 1 screen.** Rate production checkpoint 9 from four cameras and name the first fix.
4. **Optional timed fix.** Open two anonymous final scenes in Blender with the page's timer running, stopping at 20 minutes each, and record what you fixed and what remains.

## What changed from the earlier protocol

- The old continuity form asked for 96 separate scores (4 workflows × 4 stages × 6 criteria) across 102 small images. Each workflow now gets two answers.
- The short comparison's gallery is left out. You already gave preferences there and have seen two of its method assignments, so it is no longer blind.
- The picks are built from decisions agents already made: the three rejected terrain studies against the unchanged scene, the rejected vegetation and planting passes against their accepted versions, and all three overnight canopy candidates against each other. Your choices show how often you agree with those decisions.

## For the coordinator

- `runs/artist-review-2026-10-06/build_review.py` built the page's images, anonymous labels, pair order and sides, and the repair copies. Its `private/key.json` maps workflows, pairs and repair scenes back to their sources and methods. Do not show the key to the reviewer before every answer is saved.
- Answers live in the page's `answers` collection, one document per screen, and can be read with the artifact data tool. Write the summary to `docs/studies/ARTIST_REVIEW_RESULTS.md` and update E1–E3 in the [build plan](../BUILD_PLAN.md).
- The page's images are 960 × 540 for the courtyards and up to 1680 × 945 for the shed, converted from PNG to high-quality JPEG. Full screen enlarges them, but cannot add detail the renders don't have.
