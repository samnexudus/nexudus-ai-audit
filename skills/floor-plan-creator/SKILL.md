---
name: floor-plan-creator
description: Extract walls and rooms from a floor plan image and create a corresponding FloorPlanLayout in Nexudus. Use when the user shares a floor plan image and asks to "create a floor plan", "map this floor plan", "import this layout", "build this floor plan in Nexudus", or any similar phrase that pairs an image with a Nexudus floor plan goal.
---

# Floor Plan Creator

Turn a floor plan image into a Nexudus `FloorPlanLayout` with all its nodes, edges, and areas. The skill orchestrates a vision extraction pass, a deterministic geometry-cleanup script, a preview step for human review, and a commit phase that calls the `nexudus` CLI.

This skill depends on the separately-installed `nexudus` skill. If the user has not run `nexudus login` and `nexudus doctor --agent` returns `credentialsStored: false`, stop and tell them to log in first.

## Inputs you must collect

Before extracting anything, ensure you have:

1. **Floor plan image** — provided in the conversation (PNG/JPG).
2. **Calibration reference** — at least one known real-world dimension. Ask the user: *"What's one dimension you know for certain? E.g. 'the staff workstations room is 9.8m wide' or 'the building is 24m wide'."* You will need this to convert pixel measurements to millimetres. Do not guess or infer scale from generic floor plan conventions.
3. **Plan name** — e.g. "First Floor".
4. **Floor level** — integer, defaults to `0` if not specified.
5. **Target business** — call `nexudus whoami --agent` and use `DefaultBusinessId` unless the user says otherwise.

If any of these are missing, ask for them before proceeding.

## Phase 1 — Vision extraction

Look at the floor plan image and produce a **raw extraction JSON** with this exact shape:

```json
{
  "image": { "widthPx": 1920, "heightPx": 1080 },
  "calibration": {
    "knownDescription": "staff workstations interior width",
    "knownPx": 480,
    "knownMm": 9800
  },
  "rooms": [
    {
      "label": "Staff Workstations",
      "polygonPx": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    }
  ],
  "walls": [
    { "fromPx": [x1, y1], "toPx": [x2, y2] }
  ]
}
```

Rules:

- **Coordinates are pixel positions on the source image**, with origin top-left.
- **Polygons must be ordered** (CW or CCW, consistent). They define each room's perimeter.
- **Walls are the line segments forming room boundaries.** Trace every wall you see, including interior partitions. Do not include door swings, furniture, or text labels as walls.
- **Each polygon vertex should coincide with a wall endpoint.** Use the same pixel position for shared corners between rooms (don't let two rooms have near-but-not-identical corner points — pick the same coordinate).
- **Do not invent rooms** that aren't visibly enclosed by walls. If a label like "Reception Area" sits in a hallway with no walls around it, omit it (or call it out for the user).
- **Pick a clear, unambiguous calibration segment** — a long, axis-aligned wall is best. Measure it carefully on the image.

Write the raw JSON to `/tmp/floor-plan-raw.json`. Show the user a brief summary (e.g. "Detected 9 rooms and 41 wall segments") and confirm before proceeding.

## Phase 2 — Normalisation

Run the geometry cleanup script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/normalise.py" \
  --input /tmp/floor-plan-raw.json \
  --output /tmp/floor-plan-clean.json \
  --name "First Floor" \
  --floor-level 0
```

The script will:
- Convert pixel coords to millimetres using the calibration
- Snap walls to right angles (orthogonal floor plans only — most are)
- Snap node positions to a 100mm grid
- Dedupe nodes within 300mm tolerance and rewrite edge/area references
- Compute each edge's `angle`, `length`, and assign default `width: 200`, `height: 2600`
- Compute each area's `size` (m²) from its polygon
- Generate stable UUIDs for nodes and edges
- Validate that every area polygon closes and references existing nodes
- Output the Nexudus-shaped JSON

If the script exits non-zero, read its error output, explain to the user what went wrong (usually: a polygon that doesn't close, or a calibration issue), and offer to re-run extraction.

## Phase 3 — Preview

Generate an SVG overlay so the user can visually confirm:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preview_svg.py" \
  --input /tmp/floor-plan-clean.json \
  --output /tmp/floor-plan-preview.svg
```

Tell the user the preview is at `/tmp/floor-plan-preview.svg` and ask them to open it. Wait for their feedback. Common feedback patterns:

- *"Conference room should be wider"* → edit the relevant nodes' x/y in `/tmp/floor-plan-clean.json` directly, re-run the preview.
- *"Missing a room"* → add to the JSON, re-run.
- *"Looks good"* → proceed to commit.

## Phase 4 — Commit

Read the data model reference at `${CLAUDE_PLUGIN_ROOT}/skills/floor-plan-creator/references/nexudus-data-model.md` if you need to double-check field shapes.

**Confirm with the user before any write.** State: "I'm about to create a FloorPlanLayout named 'X' under business 'Y' with N nodes, M edges, and K areas. Proceed?" Wait for explicit yes.

Then execute, **in this order**:

### 4.1 Create the layout

```bash
nexudus floorplanlayouts create \
  --business-id <BusinessId> \
  --name "<plan name>" \
  --size 0 \
  --background-image-scale 0 \
  --tracing-image-scale 1917 \
  --floor-level <level> \
  --agent
```

Capture `data.Id` from the response — this is `<layoutId>`.

### 4.2 Create every node

For each node in the cleaned JSON:

```bash
nexudus floorplanlayoutnodes create \
  --floor-plan-layout-id <layoutId> \
  --node-key <node.key> \
  --pos-x <node.x> \
  --pos-y <node.y> \
  --agent
```

Use the node's pre-generated UUID as `--node-key`. **Do not re-generate UUIDs at this stage** — the edges and areas reference them.

### 4.3 Create every edge

For each edge:

```bash
nexudus floorplanlayoutedges create \
  --floor-plan-layout-id <layoutId> \
  --edge-key <edge.key> \
  --source <edge.source> \
  --target <edge.target> \
  --angle <edge.angle> \
  --width 200 \
  --height 2600 \
  --length <edge.length> \
  --is-partition false \
  --agent
```

### 4.4 Create every area

For each area, repeat the `--nodes` flag once per node UUID (this is the correct CLI convention for list options):

```bash
nexudus floorplanlayoutareas create \
  --floor-plan-layout-id <layoutId> \
  --name "<area.name>" \
  --size <area.size> \
  --color "#ffffff" \
  --nodes <area.nodes[0]> \
  --nodes <area.nodes[1]> \
  --nodes <area.nodes[2]> \
  ...
  --agent
```

### 4.5 Verify

After all writes complete, run:

```bash
nexudus floorplanlayouts get <layoutId> --agent
```

Confirm the response contains the expected counts of nodes/edges/areas and report success to the user with the layout ID.

## Failure handling

- **Mid-commit failure** (e.g. a node create fails part-way through): stop. Report which entities were created. Offer to roll back by deleting them, or to retry the remaining ones.
- **Vision misread**: if the user says the extraction missed rooms or got geometry wrong, prefer re-running Phase 1 with a more specific prompt rather than hand-patching the raw JSON.
- **Calibration off**: if all room sizes look ~10% wrong, the calibration was wrong. Ask for a different reference dimension and re-normalise from the raw JSON (no need to re-extract).

## Evaluating accuracy against a ground-truth layout

When the user wants to measure how well an extraction matched a known-good layout (e.g. one they built manually in the Nexudus UI), use the `fetch_layout.py` and `compare.py` scripts.

### Pull the reference layout

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_layout.py" <reference-layout-id> --output /tmp/reference.json
```

### Pull the attempt layout (the one the plugin just created)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_layout.py" <attempt-layout-id> --output /tmp/attempt.json
```

### Run the diff

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compare.py" \
  --reference /tmp/reference.json \
  --attempt /tmp/attempt.json \
  --report-json /tmp/compare-report.json
```

The script ignores UUIDs (matches nodes by position, areas by name) and reports: matched/missing/extra counts for nodes/edges/areas, average + max position drift, edge length outliers, area size drift > 5%, and polygon mismatches. It exits non-zero if anything material is wrong.

Use the report to decide where to focus improvements:

| Symptom | Likely cause | Fix location |
|---|---|---|
| Many missing nodes | Vision missed walls | Improve the extraction prompt in this SKILL.md |
| All nodes drift uniformly | Calibration off | Ask the user for a different known dimension and re-normalise |
| Some areas missing entirely | Vision missed rooms | Improve extraction prompt; consider two-pass extraction |
| Area sizes drift > 5% but polygons match | Cluster tolerance too loose | Tune `--cluster-tolerance-mm` lower |
| Polygon mismatches but rooms exist | Shared corners weren't deduped | Tune `--cluster-tolerance-mm` higher |

## Out of scope for v1

- Doors and windows (`FloorPlanLayoutOpening`)
- Furniture (`FloorPlanLayoutAsset`)
- Background tracing image upload — for now, the layout is created without a background image and the user can attach one manually in Nexudus if they want one.
- Linking the layout to a `FloorPlan` (which would let it be used by booking).

These are deliberate v1 omissions; the user knows.
