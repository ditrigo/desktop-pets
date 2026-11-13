"""Bake fabric/feather intersections into SVG paths for Qt's SVG renderer.

The runtime SVG subset does not implement clipPath. Boolean operations happen
only when artwork is built; shipped parts remain scalable SVG paths.
"""

import math
import re
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


def contours(d):
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", d)
    result = []
    points = []
    i = 0
    cmd = None
    pos = (0, 0)
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
        if cmd == "Z":
            if points:
                result.append((points, True))
                points = []
            cmd = None
            continue
        assert cmd in ("M", "L", "Q", "C"), ("unsupported vector command", cmd)
        n = {"M": 2, "L": 2, "Q": 4, "C": 6}[cmd]
        args = list(map(float, tokens[i : i + n]))
        i += n
        if cmd == "M":
            if points:
                result.append((points, False))
            pos = tuple(args)
            points = [pos]
            cmd = "L"
        elif cmd == "L":
            pos = tuple(args)
            points.append(pos)
        else:
            start = pos
            for step in range(1, 25):
                t = step / 24
                u = 1 - t
                if cmd == "Q":
                    p = tuple(
                        u * u * start[k] + 2 * u * t * args[k] + t * t * args[k + 2]
                        for k in (0, 1)
                    )
                else:
                    p = tuple(
                        u**3 * start[k]
                        + 3 * u * u * t * args[k]
                        + 3 * u * t * t * args[k + 2]
                        + t**3 * args[k + 4]
                        for k in (0, 1)
                    )
                points.append(p)
            pos = tuple(args[-2:])
    if points:
        result.append((points, False))
    return result


def path_geometry(d):
    return unary_union(
        [
            Polygon(points).buffer(0)
            for points, closed in contours(d)
            if len(points) >= 3
        ]
    )


def ellipse_points(x, y, w, h):
    return [
        (
            x + w / 2 + w / 2 * math.cos(i * math.tau / 64),
            y + h / 2 + h / 2 * math.sin(i * math.tau / 64),
        )
        for i in range(64)
    ]


def svg_geometry(geometry, fill):
    if geometry.is_empty:
        return ""
    polygons = (
        [geometry]
        if geometry.geom_type == "Polygon"
        else [p for p in geometry.geoms if p.geom_type == "Polygon"]
    )
    rings = []
    for polygon in polygons:
        for ring in [polygon.exterior, *polygon.interiors]:
            points = list(ring.coords)
            rings.append("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in points) + " Z")
    return (
        '<path d="' + " ".join(rings) + f'" fill="{fill}" fill-rule="evenodd"/>'
        if rings
        else ""
    )


def clipped(d, fill, stroke, width, mask):
    result = ""
    if fill != "none":
        result += svg_geometry(path_geometry(d).intersection(mask), fill)
    if stroke:
        lines = []
        for points, closed in contours(d):
            if closed:
                points = points + [points[0]]
            if len(points) >= 2:
                lines.append(LineString(points).buffer(width / 2, quad_segs=6))
        result += svg_geometry(unary_union(lines).intersection(mask), stroke)
    return result
