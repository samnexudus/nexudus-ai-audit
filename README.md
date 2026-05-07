# Nexudus Floor Plan Creator

A Claude Code plugin that turns a floor plan image into a Nexudus `FloorPlanLayout`. Drop an image into the chat, give one calibration dimension, review the extracted geometry, then commit.

## What it does

1. **Extract** — Claude looks at your floor plan image and identifies walls and rooms.
2. **Normalise** — A geometry-cleanup script snaps walls to right angles, dedupes nodes, computes lengths and areas in real-world units.
3. **Preview** — Renders an SVG so you can verify the layout is correct before anything is written to Nexudus.
4. **Commit** — Creates the `FloorPlanLayout` plus all its nodes, edges, and areas via the `nexudus` CLI.

## Requirements

- [Claude Code](https://docs.claude.com/claude-code)
- The [`nexudus` CLI](https://github.com/nexudus/nexudus-cli) installed and authenticated (`nexudus login`)
- Python 3.8+ (uses standard library only — no third-party dependencies)
- The `nexudus` Claude Code skill installed (the plugin assumes its CLI knowledge is available)

## Install

Clone this repo and install as a local plugin:

```bash
git clone <repo-url> nexudus-floor-plan-creator
# In Claude Code:
/plugin install ./nexudus-floor-plan-creator
```

## Use

In any Claude Code session:

```
You: Create a Nexudus floor plan from this image — the staff workstations
     room is 9.8m wide. Call it "First Floor".
     [attach image]
```

Claude will:

1. Confirm the inputs and Nexudus business
2. Extract walls and rooms from the image
3. Run normalisation, show counts (e.g. "Extracted 9 rooms and 41 walls")
4. Generate `/tmp/floor-plan-preview.svg` for you to review
5. Wait for your "looks good" before writing anything to Nexudus
6. Create the layout and report the layout ID

## What's supported in v1

- Walls (`FloorPlanLayoutEdge`)
- Wall corners (`FloorPlanLayoutNode`)
- Rooms (`FloorPlanLayoutArea`)

## Not yet supported

- Doors and windows (`FloorPlanLayoutOpening`)
- Furniture (`FloorPlanLayoutAsset`)
- Background tracing image upload (Nexudus's image API requires a public URL — for v1 the layout is created without a tracing image; you can upload one manually in the Nexudus UI)
- Linking the layout to a `FloorPlan` so it becomes bookable

## How precision works

Floor plan images don't usually carry a scale, so the plugin **always asks for one known dimension** (e.g. "the staff workstations are 9.8m wide"). Everything else — wall lengths, room areas — is derived from that single calibration. Pick a long, axis-aligned wall for the best accuracy.

The geometry script then:

- Clusters all x-coordinates that are within 300mm of each other (and same for y) so walls that should align actually do
- Snaps everything to a 100mm grid
- Defaults walls to 200mm thick and 2.6m tall (standard interior wall)

If your floor plan is **not** orthogonal (curved walls, walls at non-90° angles), the v1 normaliser will distort it. Open an issue or extend the script.

## Improving accuracy: the eval loop

Vision extraction is imperfect. To measure and improve it, build a ground-truth layout in Nexudus manually for a representative floor plan, then diff the plugin's output against it:

```bash
# Pull both layouts as JSON
python3 scripts/fetch_layout.py <ground-truth-id> --output /tmp/reference.json
python3 scripts/fetch_layout.py <attempt-id>      --output /tmp/attempt.json

# Diff — ignores UUIDs, matches nodes by position and areas by name
python3 scripts/compare.py --reference /tmp/reference.json --attempt /tmp/attempt.json
```

The diff reports matched/missing/extra counts, position drift, edge-length outliers, and area-size drift. Use it as a regression check after every change to `SKILL.md` (vision prompt) or `normalise.py` (geometry cleanup). The script exits non-zero on any material drift, so you can wire it into a test loop.

## Files

```
.claude-plugin/plugin.json              Plugin manifest
skills/floor-plan-creator/
  SKILL.md                              Workflow instructions for Claude
  references/nexudus-data-model.md      Schema reference for the layout JSON
scripts/
  normalise.py                          Px → mm + geometry cleanup
  preview_svg.py                        SVG renderer for the cleaned layout
  fetch_layout.py                       Pull a Nexudus layout as cleaned JSON
  compare.py                            Structural diff of two cleaned layouts
```
