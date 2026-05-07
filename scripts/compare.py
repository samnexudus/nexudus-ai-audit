#!/usr/bin/env python3
"""
Structurally compare two cleaned floor plan layouts (the format produced by
normalise.py and fetch_layout.py). Use to evaluate plugin output against a
manually-built ground-truth layout.

UUIDs are ignored — nodes are matched by position, edges by node pairs, and
areas by name. The diff report calls out missing/extra rooms, position drift,
length drift, and area-size drift.
"""
import argparse
import json
import math
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def match_nodes(ref_nodes, att_nodes, tol_mm):
    """Greedy nearest-neighbour match of attempt nodes to reference nodes.

    Returns:
      ref_to_att: dict ref_uuid -> attempt_uuid (only matched pairs)
      unmatched_ref: list of ref uuids with no attempt within tol
      unmatched_att: list of attempt uuids not used
      drifts: list of (ref_uuid, distance_mm) for matched pairs
    """
    ref_to_att = {}
    drifts = []
    used_att = set()

    candidates = []  # (distance, ref_uuid, att_uuid)
    for r in ref_nodes:
        for a in att_nodes:
            d = math.hypot(r["x"] - a["x"], r["y"] - a["y"])
            if d <= tol_mm:
                candidates.append((d, r["key"], a["key"]))

    candidates.sort()
    matched_ref = set()
    for d, r_uid, a_uid in candidates:
        if r_uid in matched_ref or a_uid in used_att:
            continue
        ref_to_att[r_uid] = a_uid
        used_att.add(a_uid)
        matched_ref.add(r_uid)
        drifts.append((r_uid, d))

    unmatched_ref = [n["key"] for n in ref_nodes if n["key"] not in matched_ref]
    unmatched_att = [n["key"] for n in att_nodes if n["key"] not in used_att]
    return ref_to_att, unmatched_ref, unmatched_att, drifts


def edge_key(src, tgt):
    return tuple(sorted((src, tgt)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True, help="Ground-truth layout JSON")
    ap.add_argument("--attempt", required=True, help="Plugin-produced layout JSON")
    ap.add_argument("--node-tolerance-mm", type=int, default=300,
                    help="Max distance between matched nodes.")
    ap.add_argument("--length-tolerance-mm", type=int, default=200,
                    help="Tolerable difference in edge length.")
    ap.add_argument("--area-tolerance-pct", type=float, default=5.0,
                    help="Tolerable percentage drift in area size.")
    ap.add_argument("--report-json", help="Optional: write structured report here.")
    args = ap.parse_args()

    ref = load(args.reference)
    att = load(args.attempt)

    report = {
        "reference": {
            "name": ref.get("name"),
            "nodes": len(ref["nodes"]),
            "edges": len(ref["edges"]),
            "areas": len(ref["areas"]),
        },
        "attempt": {
            "name": att.get("name"),
            "nodes": len(att["nodes"]),
            "edges": len(att["edges"]),
            "areas": len(att["areas"]),
        },
        "nodes": {},
        "edges": {},
        "areas": {},
    }

    # ── Node matching ─────────────────────────────────────────
    ref_to_att, ref_only, att_only, drifts = match_nodes(
        ref["nodes"], att["nodes"], args.node_tolerance_mm
    )
    matched = len(ref_to_att)
    drift_values = [d for _, d in drifts]
    report["nodes"] = {
        "matched": matched,
        "missing_in_attempt": len(ref_only),
        "extra_in_attempt": len(att_only),
        "max_drift_mm": round(max(drift_values), 1) if drift_values else 0,
        "avg_drift_mm": round(sum(drift_values) / len(drift_values), 1) if drift_values else 0,
    }

    # ── Edge matching (by mapped node pair) ───────────────────
    att_edges_by_pair = {}
    for e in att["edges"]:
        att_edges_by_pair.setdefault(edge_key(e["source"], e["target"]), []).append(e)

    edge_matched = 0
    edge_missing = 0
    edge_length_drift = []
    edge_only_in_attempt_count = len(att["edges"])
    used_att_edges = set()

    for re in ref["edges"]:
        a_src = ref_to_att.get(re["source"])
        a_tgt = ref_to_att.get(re["target"])
        if not a_src or not a_tgt:
            edge_missing += 1
            continue
        key = edge_key(a_src, a_tgt)
        candidates = [
            ae for ae in att_edges_by_pair.get(key, [])
            if id(ae) not in used_att_edges
        ]
        if not candidates:
            edge_missing += 1
            continue
        ae = candidates[0]
        used_att_edges.add(id(ae))
        edge_matched += 1
        edge_only_in_attempt_count -= 1
        delta = abs(re["length"] - ae["length"])
        if delta > args.length_tolerance_mm:
            edge_length_drift.append({
                "ref_length": re["length"],
                "att_length": ae["length"],
                "delta_mm": delta,
            })

    report["edges"] = {
        "matched": edge_matched,
        "missing_in_attempt": edge_missing,
        "extra_in_attempt": edge_only_in_attempt_count,
        "length_outliers": edge_length_drift,
    }

    # ── Area matching (by name, case-insensitive) ─────────────
    ref_by_name = {a["name"].strip().lower(): a for a in ref["areas"]}
    att_by_name = {a["name"].strip().lower(): a for a in att["areas"]}

    name_matches = sorted(set(ref_by_name) & set(att_by_name))
    missing_areas = sorted(set(ref_by_name) - set(att_by_name))
    extra_areas = sorted(set(att_by_name) - set(ref_by_name))

    area_size_drift = []
    polygon_mismatches = []
    for name in name_matches:
        r_area = ref_by_name[name]
        a_area = att_by_name[name]
        if r_area["size"] > 0:
            pct = abs(r_area["size"] - a_area["size"]) / r_area["size"] * 100.0
        else:
            pct = 0.0
        if pct > args.area_tolerance_pct:
            area_size_drift.append({
                "name": r_area["name"],
                "ref_size": r_area["size"],
                "att_size": a_area["size"],
                "pct_drift": round(pct, 2),
            })
        # polygon: check vertex count and that each ref vertex maps to one in attempt polygon
        r_poly_mapped = [ref_to_att.get(uid) for uid in r_area["nodes"]]
        if any(x is None for x in r_poly_mapped):
            polygon_mismatches.append({
                "name": r_area["name"],
                "issue": "ref polygon contains nodes that didn't match any attempt node",
            })
        elif len(r_poly_mapped) != len(a_area["nodes"]):
            polygon_mismatches.append({
                "name": r_area["name"],
                "issue": f"vertex count differs: ref={len(r_poly_mapped)} att={len(a_area['nodes'])}",
            })
        elif set(r_poly_mapped) != set(a_area["nodes"]):
            polygon_mismatches.append({
                "name": r_area["name"],
                "issue": "polygon node set differs after mapping",
            })

    report["areas"] = {
        "matched": len(name_matches),
        "missing_in_attempt": missing_areas,
        "extra_in_attempt": extra_areas,
        "size_outliers": area_size_drift,
        "polygon_mismatches": polygon_mismatches,
    }

    # ── Human-readable summary ────────────────────────────────
    print(f"Reference: {report['reference']}")
    print(f"Attempt:   {report['attempt']}")
    print()
    print("NODES")
    print(f"  matched: {report['nodes']['matched']}")
    print(f"  missing in attempt: {report['nodes']['missing_in_attempt']}")
    print(f"  extra in attempt:   {report['nodes']['extra_in_attempt']}")
    print(f"  drift: max {report['nodes']['max_drift_mm']}mm, avg {report['nodes']['avg_drift_mm']}mm")
    print()
    print("EDGES")
    print(f"  matched: {report['edges']['matched']}")
    print(f"  missing in attempt: {report['edges']['missing_in_attempt']}")
    print(f"  extra in attempt:   {report['edges']['extra_in_attempt']}")
    print(f"  length outliers: {len(report['edges']['length_outliers'])}")
    print()
    print("AREAS")
    print(f"  matched: {report['areas']['matched']}")
    if report['areas']['missing_in_attempt']:
        print(f"  missing: {report['areas']['missing_in_attempt']}")
    if report['areas']['extra_in_attempt']:
        print(f"  extra:   {report['areas']['extra_in_attempt']}")
    if report['areas']['size_outliers']:
        print(f"  size outliers (>{args.area_tolerance_pct}% drift):")
        for s in report['areas']['size_outliers']:
            print(f"    {s['name']}: ref={s['ref_size']}m² att={s['att_size']}m² "
                  f"({s['pct_drift']}%)")
    if report['areas']['polygon_mismatches']:
        print(f"  polygon mismatches:")
        for p in report['areas']['polygon_mismatches']:
            print(f"    {p['name']}: {p['issue']}")

    if args.report_json:
        with open(args.report_json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nFull report: {args.report_json}")

    # Exit non-zero if anything material is wrong
    fail = (
        report['nodes']['missing_in_attempt'] > 0
        or report['edges']['missing_in_attempt'] > 0
        or report['areas']['missing_in_attempt']
        or report['areas']['size_outliers']
        or report['areas']['polygon_mismatches']
    )
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
