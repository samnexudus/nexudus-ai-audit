#!/usr/bin/env python3
"""
Normalise a raw floor plan extraction JSON into a Nexudus-shaped layout JSON.

Input shape (raw, as produced by the vision pass):
{
  "image": { "widthPx": int, "heightPx": int },
  "calibration": { "knownPx": float, "knownMm": float, "knownDescription": str },
  "rooms": [ { "label": str, "polygonPx": [[x,y], ...] } ],
  "walls": [ { "fromPx": [x,y], "toPx": [x,y] } ]
}

Output shape (cleaned, ready to commit):
{
  "name": str,
  "floorLevel": int,
  "nodes": [ { "key": uuid, "x": int_mm, "y": int_mm } ],
  "edges": [ { "key": uuid, "source": uuid, "target": uuid,
               "angle": float_deg, "length": int_mm,
               "width": int_mm, "height": int_mm,
               "isPartition": bool, "openings": [] } ],
  "areas": [ { "name": str, "size": float_m2, "color": str,
               "nodes": [uuid, ...], "containedAreas": [] } ]
}
"""
import argparse
import json
import math
import sys
import uuid


def cluster_1d(values, tol):
    """Cluster a list of floats: any two values within `tol` are merged.

    Returns dict mapping each original value to its cluster centre (rounded int).
    """
    if not values:
        return {}
    sorted_vals = sorted(set(values))
    clusters = [[sorted_vals[0]]]
    for v in sorted_vals[1:]:
        if v - clusters[-1][-1] <= tol:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    mapping = {}
    for cluster in clusters:
        centre = round(sum(cluster) / len(cluster))
        for v in cluster:
            mapping[v] = centre
    return mapping


def snap_to_grid(v, grid):
    return int(round(v / grid)) * grid


def shoelace_area_mm2(polygon):
    """Polygon: list of (x_mm, y_mm). Returns absolute area in mm²."""
    n = len(polygon)
    s = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        s += (x1 * y2) - (x2 * y1)
    return abs(s) / 2.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Raw extraction JSON path")
    ap.add_argument("--output", required=True, help="Cleaned layout JSON path")
    ap.add_argument("--name", required=True, help="Layout name (e.g. 'First Floor')")
    ap.add_argument("--floor-level", type=int, default=0)
    ap.add_argument("--cluster-tolerance-mm", type=int, default=300,
                    help="Coords within this distance merge to the same node.")
    ap.add_argument("--grid-mm", type=int, default=100,
                    help="Final coordinate snap grid.")
    ap.add_argument("--wall-width-mm", type=int, default=200)
    ap.add_argument("--wall-height-mm", type=int, default=2600)
    args = ap.parse_args()

    with open(args.input) as f:
        raw = json.load(f)

    cal = raw.get("calibration") or {}
    px = cal.get("knownPx")
    mm = cal.get("knownMm")
    if not px or not mm:
        sys.exit("ERROR: calibration.knownPx and calibration.knownMm are required")
    scale = float(mm) / float(px)  # mm per pixel

    rooms = raw.get("rooms") or []
    walls = raw.get("walls") or []

    if not rooms:
        sys.exit("ERROR: no rooms in extraction — nothing to commit")

    # Collect every unique pixel point from walls + room polygons
    unique_px = set()
    for w in walls:
        unique_px.add(tuple(w["fromPx"]))
        unique_px.add(tuple(w["toPx"]))
    for r in rooms:
        for p in r["polygonPx"]:
            unique_px.add(tuple(p))

    # Convert each unique px point to mm
    mm_by_px = {p: (p[0] * scale, p[1] * scale) for p in unique_px}

    # 1D-cluster all x and y coordinates separately. This produces orthogonal
    # alignment for free: walls that should be at the same x (or y) end up there.
    xs_mm = [v[0] for v in mm_by_px.values()]
    ys_mm = [v[1] for v in mm_by_px.values()]
    x_map = cluster_1d(xs_mm, args.cluster_tolerance_mm)
    y_map = cluster_1d(ys_mm, args.cluster_tolerance_mm)

    def to_canonical(p_px):
        mm_pt = mm_by_px[tuple(p_px)]
        sx = snap_to_grid(x_map[mm_pt[0]], args.grid_mm)
        sy = snap_to_grid(y_map[mm_pt[1]], args.grid_mm)
        return (sx, sy)

    # Build canonical node table
    node_uuid_by_xy = {}
    nodes = []

    def get_node(p_px):
        xy = to_canonical(p_px)
        if xy not in node_uuid_by_xy:
            uid = str(uuid.uuid4())
            node_uuid_by_xy[xy] = uid
            nodes.append({"key": uid, "x": xy[0], "y": xy[1]})
        return node_uuid_by_xy[xy]

    node_xy_by_uuid = {}  # populated as we go

    def remember(uid, xy):
        node_xy_by_uuid[uid] = xy

    # Build edges
    edges = []
    seen_edges = set()
    for w in walls:
        a_uid = get_node(w["fromPx"])
        b_uid = get_node(w["toPx"])
        remember(a_uid, to_canonical(w["fromPx"]))
        remember(b_uid, to_canonical(w["toPx"]))
        if a_uid == b_uid:
            continue  # degenerate after snapping
        canon = tuple(sorted((a_uid, b_uid)))
        if canon in seen_edges:
            continue  # dedupe shared walls
        seen_edges.add(canon)
        ax, ay = node_xy_by_uuid[a_uid]
        bx, by = node_xy_by_uuid[b_uid]
        dx, dy = bx - ax, by - ay
        length = int(round(math.hypot(dx, dy)))
        angle_deg = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
        edges.append({
            "key": str(uuid.uuid4()),
            "source": a_uid,
            "target": b_uid,
            "angle": round(angle_deg, 5),
            "length": length,
            "width": args.wall_width_mm,
            "height": args.wall_height_mm,
            "isPartition": False,
            "openings": [],
        })

    # Build areas
    areas = []
    warnings = []
    for r in rooms:
        polygon_uuids = []
        for p_px in r["polygonPx"]:
            uid = get_node(p_px)
            remember(uid, to_canonical(p_px))
            if polygon_uuids and polygon_uuids[-1] == uid:
                continue  # consecutive duplicates from snapping
            polygon_uuids.append(uid)
        # also collapse if first==last
        if len(polygon_uuids) > 1 and polygon_uuids[0] == polygon_uuids[-1]:
            polygon_uuids = polygon_uuids[:-1]
        if len(polygon_uuids) < 3:
            warnings.append(
                f"room '{r['label']}' collapsed to <3 vertices; skipped"
            )
            continue
        polygon_xy = [node_xy_by_uuid[uid] for uid in polygon_uuids]
        size_mm2 = shoelace_area_mm2(polygon_xy)
        size_m2 = round(size_mm2 / 1_000_000.0, 2)
        areas.append({
            "name": r["label"],
            "size": size_m2,
            "color": "#ffffff",
            "nodes": polygon_uuids,
            "containedAreas": [],
        })

    # Validation
    node_keys = {n["key"] for n in nodes}
    for e in edges:
        if e["source"] not in node_keys or e["target"] not in node_keys:
            sys.exit(f"ERROR: edge {e['key']} references missing node")
    for a in areas:
        for n in a["nodes"]:
            if n not in node_keys:
                sys.exit(f"ERROR: area '{a['name']}' references missing node {n}")

    out = {
        "name": args.name,
        "floorLevel": args.floor_level,
        "nodes": nodes,
        "edges": edges,
        "areas": areas,
    }

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    print(
        f"Wrote {args.output}: "
        f"{len(nodes)} nodes, {len(edges)} edges, {len(areas)} areas"
    )


if __name__ == "__main__":
    main()
