# G7 trial: StableGen, November 15

The second extension trial in build-plan item G7. It asks whether StableGen's multi-view projection texturing can give the potting-shed pots the weathered surface the realism review said they lacked, driven by an agent's script with no hand work in the UI. Three runs, one model, so the result is directional. Evidence is retained in `runs/g7-extension-trials-2026-11-15/stablegen-trial/`.

## Setup

- **Add-on.** [sakalond/StableGen](https://github.com/sakalond/StableGen) 0.5.0, GPL-3.0-or-later (`StableGen-0.5.0-windows-x64.zip`, 79 MB, SHA-256 `914f2e15…f257a86d`). Its README supports Blender 4.2 to 4.5 and 5.1 or later, and names 5.0 as unsupported. It was installed into the same separate Blender 5.2 user folder as the geometry-script trial. It was driven only through its operators and properties; no source was copied into this package.
- **ComfyUI.** StableGen's installer built its own ComfyUI 0.43.0 (Python 3.12, torch 2.9.0 for CUDA 13.0) in `runs/g7sg`, with the owner's approval. The owner's existing ComfyUI was not touched. Package 4, the complete SDXL set with the RealVisXL V5.0 checkpoint, was installed into it.
- **Subject.** The four bench pots from garden checkpoint 9, copied into a trial file. The checkpoint's hash was unchanged.
- **Driver.** A Python script inside a windowed Blender 5.2.1 sets the preferences and prompt, applies StableGen's `DEFAULT` preset, places cameras, starts generation, polls, bakes to image textures and saves.

## Cost

| Item | Measured |
|---|---|
| Disk, StableGen's ComfyUI with the SDXL package | 32 GB |
| Download and install time | About 15 minutes |
| Peak GPU memory during generation | 13.9 GB of 48 GB (RTX A6000), against 3.0 GB idle |
| Run 2: four pots, three cameras, 1024 px bake | 47 s |
| Run 3: one pot, eight cameras, 1024 px bake | 101 s |

## Runs

| Run | What was asked | Outcome |
|---|---|---|
| 1 | All four pots | Failed in my driver before generating: the checkpoint list holds tuples and I passed one whole. No StableGen fault |
| 2 | All four pots as one job, six hemisphere cameras requested | Completed, poor result |
| 3 | The small pot alone, eight hemisphere cameras, prompt for one empty pot | Completed, good result |

**Run 2** produced only three cameras for the four pots, which are spread 1.4 m along the bench. Each view held all four pots in one tall frame, so each pot got few pixels. The baked result has unpainted black areas where no camera saw the surface, visible seams between views, and plants painted into pots that should be empty. In this mode every mesh's first material slot was also replaced with the same material.

**Run 3** covered the pot completely. The baked texture reads as weathered terracotta with pale salt staining, a worn rim and tonal variation, which is the character the realism review asked for. The other three pots were unchanged: same materials, UV layers and vertex counts.

## What it shows

- **It can be driven by script, but only in a window.** Generation and baking are modal operators with timers, as the plan expected. They do nothing in background Blender. The script polls `ComfyUIGenerate._is_running` and the window's modal operators from an application timer, which is the pattern StableGen's own batch code uses.
- **It needs online access switched on** in Blender, and a running ComfyUI server.
- **One object at a time is the workable unit.** Texturing several separated objects as one job starved each of pixels and coverage.
- **It changes more than the texture.** On the targeted mesh it adds a second material slot and moves every face to it, adds a `BakeUV` layer, and leaves eight cameras in the scene. The baked images are external files in its run folder, not packed. A harness edit would need a contract that permits those fields on the target, and would have to remove the cameras and pack the images before a checkpoint.
- **The model invents content.** With "garden still life" in the prompt it painted plants into empty pots. The prompt has to describe one object against a plain background.
- **Reproducibility was not tested.** The seed was fixed, but no run was repeated, so whether a retained script regenerates the same texture is unknown. Treat the baked image as the thing to keep.
- **A note on the file it leaves.** The file StableGen saved rendered nothing from its own scene in background Blender; its meshes rendered normally once appended into a clean scene. I did not find the cause.

## Not done

- **Painted surfaces.** The plan also named the shed's painted surfaces. Only the pots were tried.
- **A judged comparison.** I looked at the before and after renders myself. No fresh judge or owner review was run.
- **Qwen Image and the PBR map packages** (roughness, normal). Only SDXL colour was tried.

## Decision

**Kept as an optional, owner-run tool, outside the default path.** The owner accepted this recommendation on November 15.

## Recommendation

**Keep it as an optional, owner-run tool; do not make it part of the default path.**

- The result on a single object is what the scenes lack and what procedural shaders in this project have not produced.
- The costs are real: 32 GB of disk, a GPL add-on, a windowed Blender, online access, and a second ComfyUI or changes to the owner's.
- It does not fit the harness's fresh background worker, so it cannot run under managed execution as it stands. The route that fits is the frozen asynchronous add-on recipe, which was built for submit-poll-collect providers; qualifying StableGen through it would also satisfy the G8 condition for unfreezing add-on capabilities.

Suggested next step if kept: one craft-skill reference, "texture one object with StableGen", stating the per-object rule, the prompt rule, and the clean-up before a checkpoint. No runtime change.

## Clean-up

`runs/g7sg` (32 GB) and `runs/g7-extension-trials-2026-11-15/blender-profile` hold the trial's ComfyUI and Blender user folder. Both are inside the git-ignored `runs/` folder and can be deleted once the decision is made. The trial's ComfyUI server was stopped.
