#!/usr/bin/env python3
"""
Fetch a Nexudus FloorPlanLayout (header + nodes + edges + areas) and write it
as a single cleaned-format JSON file, matching the shape produced by
normalise.py. Use this to capture a ground-truth reference layout (built
manually in the Nexudus UI) for use with compare.py.

Requires the `nexudus` CLI to be installed and authenticated.
"""
import argparse
import json
import subprocess
import sys


def run_cli(args):
    """Run a `nexudus` subcommand with --agent and return the parsed envelope."""
    cmd = ["nexudus", *args, "--agent"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ERROR: {' '.join(cmd)} exited {result.returncode}\n{result.stderr}")
    try:
        env = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: could not parse JSON from {' '.join(cmd)}: {exc}")
    if not env.get("ok"):
        sys.exit(f"ERROR: {env.get('summary', 'unknown error')}")
    return env


def fetch_all_pages(entity, layout_id, page_size=200):
    """Page through a list endpoint scoped to a layout, returning all records."""
    records = []
    page = 1
    while True:
        env = run_cli([
            entity, "list",
            "--floor-plan-layout-id", str(layout_id),
            "--page-number", str(page),
            "--page-size", str(page_size),
        ])
        page_records = env.get("data") or []
        records.extend(page_records)
        meta = env.get("meta") or {}
        total_pages = meta.get("totalPages") or 1
        if page >= total_pages:
            break
        page += 1
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("layout_id", type=int, help="FloorPlanLayout ID")
    ap.add_argument("--output", required=True, help="Output JSON path")
    args = ap.parse_args()

    header = run_cli(["floorplanlayouts", "get", str(args.layout_id)])["data"]
    nodes_raw = fetch_all_pages("floorplanlayoutnodes", args.layout_id)
    edges_raw = fetch_all_pages("floorplanlayoutedges", args.layout_id)
    areas_raw = fetch_all_pages("floorplanlayoutareas", args.layout_id)

    # Build node UUID lookup so we can translate edge source/target and area
    # node refs (which the API may return as integer IDs or unique IDs depending
    # on the field) into UUIDs consistently.
    node_uuid_by_id = {}
    nodes = []
    for n in nodes_raw:
        uid = n.get("UniqueId") or n.get("NodeKey")
        nid = n.get("Id")
        node_uuid_by_id[nid] = uid
        node_uuid_by_id[uid] = uid
        nodes.append({
            "key": uid,
            "x": int(n.get("PosX", 0)),
            "y": int(n.get("PosY", 0)),
        })

    def to_uuid(ref):
        if ref in node_uuid_by_id:
            return node_uuid_by_id[ref]
        return ref  # already a UUID we don't know about — pass through

    edges = []
    for e in edges_raw:
        src = e.get("Source") or e.get("SourceUniqueId")
        tgt = e.get("Target") or e.get("TargetUniqueId")
        edges.append({
            "key": e.get("UniqueId") or e.get("EdgeKey"),
            "source": to_uuid(src),
            "target": to_uuid(tgt),
            "angle": float(e.get("Angle", 0)),
            "length": int(e.get("Length", 0)),
            "width": int(e.get("Width", 200)),
            "height": int(e.get("Height", 2600)),
            "isPartition": bool(e.get("IsPartition", False)),
            "openings": [],
        })

    areas = []
    for a in areas_raw:
        node_refs = a.get("Nodes") or []
        # `Nodes` may come back as a list of UUIDs, ints, or comma-separated
        # string. Normalise.
        if isinstance(node_refs, str):
            node_refs = [r.strip() for r in node_refs.split(",") if r.strip()]
        node_uuids = [to_uuid(r) for r in node_refs]
        areas.append({
            "name": a.get("Name", ""),
            "size": float(a.get("Size", 0)),
            "color": a.get("Color") or "#ffffff",
            "nodes": node_uuids,
            "containedAreas": [],
        })

    out = {
        "name": header.get("Name", ""),
        "floorLevel": int(header.get("FloorLevel", 0)),
        "nodes": nodes,
        "edges": edges,
        "areas": areas,
    }

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)

    print(
        f"Wrote {args.output}: "
        f"{len(nodes)} nodes, {len(edges)} edges, {len(areas)} areas "
        f"(layout {args.layout_id} '{out['name']}')"
    )


if __name__ == "__main__":
    main()
