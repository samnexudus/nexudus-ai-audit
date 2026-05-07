#!/usr/bin/env python3
"""
Render a cleaned floor plan layout JSON as an SVG so the user can review
before committing to Nexudus.

Reads the output of normalise.py. SVG uses millimetre coordinates with the
y-axis growing downwards (matches the source image and Nexudus convention).
"""
import argparse
import json
import sys
from xml.sax.saxutils import escape


PADDING_MM = 1000  # margin around the layout
ROOM_FILL = "#e8f1ff"
ROOM_STROKE = "#9ab8d8"
WALL_STROKE = "#333333"
NODE_FILL = "#cc4444"
LABEL_FILL = "#222222"
GRID_STROKE = "#eeeeee"
GRID_STEP_MM = 1000


def centroid(points):
    n = len(points)
    cx = sum(p[0] for p in points) / n
    cy = sum(p[1] for p in points) / n
    return cx, cy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Cleaned layout JSON")
    ap.add_argument("--output", required=True, help="SVG output path")
    ap.add_argument("--width-px", type=int, default=1200,
                    help="Target SVG render width in pixels.")
    args = ap.parse_args()

    with open(args.input) as f:
        layout = json.load(f)

    nodes = layout["nodes"]
    edges = layout["edges"]
    areas = layout["areas"]

    if not nodes:
        sys.exit("ERROR: layout has no nodes")

    node_by_key = {n["key"]: n for n in nodes}

    xs = [n["x"] for n in nodes]
    ys = [n["y"] for n in nodes]
    min_x, max_x = min(xs) - PADDING_MM, max(xs) + PADDING_MM
    min_y, max_y = min(ys) - PADDING_MM, max(ys) + PADDING_MM
    width = max_x - min_x
    height = max_y - min_y

    # SVG units = mm. We set width in pixels, height auto via viewBox.
    px_w = args.width_px
    px_h = int(round(px_w * height / width))

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{px_w}" height="{px_h}" '
        f'viewBox="{min_x} {min_y} {width} {height}" '
        f'font-family="sans-serif">'
    )
    parts.append(f'<rect x="{min_x}" y="{min_y}" width="{width}" height="{height}" fill="white"/>')

    # 1m grid
    parts.append(f'<g stroke="{GRID_STROKE}" stroke-width="20">')
    gx = (min_x // GRID_STEP_MM) * GRID_STEP_MM
    while gx <= max_x:
        parts.append(f'<line x1="{gx}" y1="{min_y}" x2="{gx}" y2="{max_y}"/>')
        gx += GRID_STEP_MM
    gy = (min_y // GRID_STEP_MM) * GRID_STEP_MM
    while gy <= max_y:
        parts.append(f'<line x1="{min_x}" y1="{gy}" x2="{max_x}" y2="{gy}"/>')
        gy += GRID_STEP_MM
    parts.append('</g>')

    # Areas (filled polygons + labels)
    for a in areas:
        pts = []
        for uid in a["nodes"]:
            if uid not in node_by_key:
                continue
            n = node_by_key[uid]
            pts.append((n["x"], n["y"]))
        if len(pts) < 3:
            continue
        points_attr = " ".join(f"{x},{y}" for x, y in pts)
        parts.append(
            f'<polygon points="{points_attr}" '
            f'fill="{ROOM_FILL}" fill-opacity="0.6" '
            f'stroke="{ROOM_STROKE}" stroke-width="40"/>'
        )
        cx, cy = centroid(pts)
        label = escape(a["name"])
        size_label = f'{a["size"]} m²'
        parts.append(
            f'<text x="{cx}" y="{cy}" font-size="350" '
            f'fill="{LABEL_FILL}" text-anchor="middle">{label}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + 400}" font-size="280" '
            f'fill="{LABEL_FILL}" text-anchor="middle" opacity="0.7">{size_label}</text>'
        )

    # Walls
    parts.append(f'<g stroke="{WALL_STROKE}" stroke-width="200" stroke-linecap="square">')
    for e in edges:
        a = node_by_key.get(e["source"])
        b = node_by_key.get(e["target"])
        if not a or not b:
            continue
        parts.append(f'<line x1="{a["x"]}" y1="{a["y"]}" x2="{b["x"]}" y2="{b["y"]}"/>')
    parts.append('</g>')

    # Nodes
    parts.append(f'<g fill="{NODE_FILL}">')
    for n in nodes:
        parts.append(f'<circle cx="{n["x"]}" cy="{n["y"]}" r="120"/>')
    parts.append('</g>')

    # Title
    title = escape(layout.get("name", "Floor plan"))
    parts.append(
        f'<text x="{min_x + 100}" y="{min_y + 600}" font-size="500" '
        f'fill="{LABEL_FILL}" font-weight="bold">{title}</text>'
    )

    parts.append('</svg>')

    with open(args.output, "w") as f:
        f.write("\n".join(parts))

    print(f"Wrote {args.output} "
          f"({len(nodes)} nodes, {len(edges)} edges, {len(areas)} areas)")


if __name__ == "__main__":
    main()
