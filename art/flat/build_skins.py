"""Draw classic vector art and independently authored 60x56 pixel skins.

All parts use the same 120x112 logical canvas. Head art uses local 64x58,
headwear 64x32 and neckwear 64x80. Anchors are in the graphics contract.
Run: uv run --with pillow --with shapely --no-project python art/flat/build_skins.py
"""

from pathlib import Path
import json
from PIL import Image, ImageDraw
import classic
import wardrobe
import vector_clip

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "src/assets/duck2d"
VIEWS = ("side", "threeQuarter", "front")
PALETTES = {
    "yellow": dict(
        body="#ffd557",
        light="#fff0a5",
        shade="#e5ae38",
        edge="#aa772c",
        head="#ffdb64",
        headlight="#ffed9b",
        headshade="#edbb45",
        wing="#eebe43",
        breast="#ffe9a1",
    ),
    "mallard": dict(
        body="#b7b2a0",
        light="#ddd6c3",
        shade="#8c8574",
        edge="#635d52",
        head="#32866f",
        headlight="#69ae8c",
        headshade="#236451",
        wing="#8d8777",
        breast="#92624b",
    ),
    "white": dict(
        body="#eeeae0",
        light="#ffffff",
        shade="#c8c7bc",
        edge="#8c9694",
        head="#f6f3e9",
        headlight="#ffffff",
        headshade="#d7d8ce",
        wing="#d9d8ca",
        breast="#fffcf0",
    ),
}


class Art:
    def __init__(self, style, w, h):
        self.pixel = style == "pixel"
        self.w = w
        self.h = h
        self.parts = []
        self.defs = []
        self.clip = None
        if self.pixel:
            self.image = Image.new("RGBA", (w // 2, h // 2))
            self.draw = ImageDraw.Draw(self.image)

    def poly(self, points, fill, outline=None, width=1):
        if isinstance(points, str):
            points = [tuple(map(float, p.split(","))) for p in points.split()]
        if self.pixel:
            pts = [(round(x / 2), round(y / 2)) for x, y in points]
            self.draw.polygon(pts, fill=fill)
            if outline:
                self.draw.line(
                    pts + [pts[0]], fill=outline, width=max(1, round(width / 2))
                )
        elif self.clip is not None:
            self.parts.append(
                vector_clip.clipped(
                    "M" + " L".join(f"{x},{y}" for x, y in points) + " Z",
                    fill,
                    outline,
                    width,
                    self.clip,
                )
            )
        else:
            self.parts.append(
                '<polygon points="'
                + " ".join(f"{x},{y}" for x, y in points)
                + f'" fill="{fill}"'
                + (
                    f' stroke="{outline}" stroke-width="{width}" stroke-linejoin="round"'
                    if outline
                    else ""
                )
                + "/>"
            )

    def rect(self, x, y, w, h, fill, r=0):
        if self.pixel:
            px, py = round(x / 2), round(y / 2)
            self.draw.rectangle(
                (px, py, px + max(1, round(w / 2)) - 1, py + max(1, round(h / 2)) - 1),
                fill=fill,
            )
        elif self.clip is not None:
            self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill)
        else:
            self.parts.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>'
            )

    def ellipse(self, x, y, w, h, fill, outline=None, width=1):
        if self.pixel:
            # Pixel silhouettes are stair-stepped polygons, never filtered ellipses.
            self.poly(
                [
                    (x + w * 0.25, y),
                    (x + w * 0.75, y),
                    (x + w * 0.75, y + 2),
                    (x + w, y + 2),
                    (x + w, y + h - 4),
                    (x + w * 0.75, y + h - 4),
                    (x + w * 0.75, y + h),
                    (x + w * 0.25, y + h),
                    (x + w * 0.25, y + h - 2),
                    (x, y + h - 2),
                    (x, y + 2),
                    (x + w * 0.25, y + 2),
                ],
                fill,
                outline,
                2,
            )
        elif self.clip is not None:
            self.poly(vector_clip.ellipse_points(x, y, w, h), fill, outline, width)
        else:
            self.parts.append(
                f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" ry="{h / 2}" fill="{fill}"'
                + (f' stroke="{outline}" stroke-width="{width}"' if outline else "")
                + "/>"
            )

    def path(self, d, fill, stroke=None, width=1):
        assert not self.pixel
        if self.clip is not None:
            self.parts.append(vector_clip.clipped(d, fill, stroke, width, self.clip))
            return
        self.parts.append(
            f'<path d="{d}" fill="{fill}"'
            + (
                f' stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"'
                if stroke
                else ""
            )
            + "/>"
        )

    def line(self, points, color, width=1):
        if self.pixel:
            self.draw.line(
                [(round(x / 2), round(y / 2)) for x, y in points],
                fill=color,
                width=max(1, round(width / 2)),
            )
        elif self.clip is not None:
            self.path(
                "M" + " L".join(f"{x},{y}" for x, y in points), "none", color, width
            )
        else:
            self.parts.append(
                '<polyline points="'
                + " ".join(f"{x},{y}" for x, y in points)
                + f'" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
            )

    def begin_clip(self, d):
        self.clip = vector_clip.path_geometry(d)

    def end_clip(self):
        self.clip = None

    def gradient(self, name, a, b):
        if self.pixel:
            return a
        self.defs.append(
            f'<linearGradient id="{name}" x1="0" y1="0" x2=".25" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
        )
        return f"url(#{name})"

    def save(self, style, name):
        folder = OUT / style
        folder.mkdir(parents=True, exist_ok=True)
        if self.pixel:
            self.image.save(folder / (name + ".png"), optimize=True)
        else:
            (folder / (name + ".svg")).write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}"><defs>'
                + "".join(self.defs)
                + "</defs>"
                + "".join(self.parts)
                + "</svg>\n"
            )


def body_shape(view, sleep):
    return classic.body_shape(view, sleep)


def pixel_body_points(view, sleep):
    dy = 12 if sleep else 0
    if view == "front":
        return [
            (42, 54 + dy),
            (76, 54 + dy),
            (76, 60 + dy),
            (84, 60 + dy),
            (84, 68 + dy),
            (88, 68 + dy),
            (88, 88),
            (82, 88),
            (82, 96),
            (70, 96),
            (70, 100),
            (46, 100),
            (46, 96),
            (36, 96),
            (36, 90),
            (30, 90),
            (30, 70 + dy),
            (34, 70 + dy),
            (34, 60 + dy),
            (42, 60 + dy),
        ]
    return [
        (42, 52 + dy),
        (74, 52 + dy),
        (74, 56 + dy),
        (84, 56 + dy),
        (84, 62 + dy),
        (90, 62 + dy),
        (90, 88),
        (84, 88),
        (84, 96),
        (74, 96),
        (74, 100),
        (44, 100),
        (44, 98),
        (32, 98),
        (32, 92),
        (26, 92),
        (26, 82),
        (22, 82),
        (22, 68 + dy),
        (28, 68 + dy),
        (28, 60 + dy),
        (36, 60 + dy),
        (36, 56 + dy),
        (42, 56 + dy),
    ]


def body(style, palette, p, view, sleep):
    a = Art(style, 120, 112)
    front = view == "front"
    dy = 12 if sleep else 0
    if a.pixel:
        if not front:
            a.poly(
                [
                    (32, 60 + dy),
                    (24, 58 + dy),
                    (14, 54 + dy),
                    (14, 66 + dy),
                    (22, 74 + dy),
                    (30, 74 + dy),
                ],
                p["shade"],
                p["edge"],
                2,
            )
        a.poly(pixel_body_points(view, sleep), p["body"], p["edge"], 2)
        a.poly(
            [
                (34, 64 + dy),
                (42, 58 + dy),
                (68, 58 + dy),
                (76, 62 + dy),
                (48, 62 + dy),
                (38, 68 + dy),
            ],
            p["light"],
        )
        a.poly(
            [
                (36, 84),
                (42, 90),
                (74, 90),
                (82, 84),
                (80, 94),
                (68, 98),
                (44, 96),
                (34, 90),
            ],
            p["shade"],
        )
        if palette == "mallard":
            a.poly(
                [
                    (68 if not front else 46, 64 + dy),
                    (82 if not front else 76, 64 + dy),
                    (82 if not front else 76, 84),
                    (72 if not front else 48, 90),
                    (64 if not front else 42, 84),
                ],
                p["breast"],
            )
    else:
        classic.body(a, p, view, sleep)
    a.save(style, f"{palette}-body-{view}" + ("-sleep" if sleep else ""))


def head(style, palette, p, view, covered):
    a = Art(style, 64, 58)
    front = view == "front"
    if a.pixel:
        a.poly(
            [(20, 36), (38, 36), (40, 42), (40, 52), (22, 52), (18, 48)]
            if front
            else [(22, 36), (40, 36), (42, 42), (42, 52), (24, 52), (20, 48)],
            p["headshade"],
            p["edge"],
            2,
        )
        a.poly(
            [
                (20, 10),
                (40, 10),
                (40, 12),
                (46, 12),
                (46, 18),
                (50, 18),
                (50, 34),
                (46, 34),
                (46, 42),
                (38, 42),
                (38, 46),
                (22, 46),
                (22, 42),
                (14, 42),
                (14, 36),
                (10, 36),
                (10, 20),
                (14, 20),
                (14, 14),
                (20, 14),
            ],
            p["head"],
            p["edge"],
            2,
        )
        a.poly(
            [(20, 14), (38, 14), (42, 18), (22, 18), (16, 24), (14, 24), (14, 20)],
            p["headlight"],
        )
        a.poly(
            [
                (16, 34),
                (22, 40),
                (38, 40),
                (44, 36),
                (44, 42),
                (36, 46),
                (22, 44),
                (16, 40),
            ],
            p["headshade"],
        )
        if not covered:
            a.poly(
                [(22, 12), (20, 4), (24, 4), (28, 10), (30, 2), (34, 2), (34, 12)],
                p["head"],
                p["edge"],
                2,
            )
        if front:
            a.poly(
                [(20, 32), (40, 32), (44, 36), (42, 42), (22, 42), (18, 38)],
                "#dd873b",
                "#a56631",
                2,
            )
            a.rect(22, 34, 18, 4, "#ffbd65")
            a.rect(24, 40, 14, 2, "#b77832")
        else:
            a.poly(
                [(44, 30), (60, 30), (62, 32), (62, 38), (58, 42), (46, 42), (42, 38)],
                "#e99a43",
                "#a56631",
                2,
            )
            a.rect(46, 32, 14, 4, "#ffc56d")
            a.rect(46, 38, 12, 2, "#bf7937")
            a.rect(52, 32, 2, 2, "#8d653c")
        if palette == "mallard":
            a.rect(24, 48, 18, 2, "#f4eed5")
    else:
        classic.head(a, p, view, covered)
    a.save(style, f"{palette}-head-{view}" + ("-covered" if covered else ""))


def eyes(style, view, state):
    a = Art(style, 64, 58)
    if a.pixel:
        coords = (
            [(20, 24, 5), (37, 24, 5)]
            if view == "front"
            else [(23, 24, 3), (37, 24, 6)]
            if view == "threeQuarter"
            else [(36, 24, 6)]
        )
        for x, y, w in coords:
            x = round(x / 2) * 2
            if state == "closed":
                a.rect(x, y + 4, 6, 2, "#35413b")
            else:
                a.rect(x, y, 6, 10 if state == "wide" else 8, "#303a37")
                a.rect(x, y, 2, 2, "#fffbea")
    else:
        classic.eyes(a, view, state)
    a.save(style, f"eyes-{view}-{state}")


def wing(style, palette, p, front):
    a = Art(style, 40, 30)
    if a.pixel:
        pts = (
            [
                (16, 4),
                (24, 4),
                (26, 8),
                (26, 18),
                (22, 18),
                (22, 24),
                (16, 28),
                (10, 28),
                (6, 24),
                (4, 18),
                (4, 10),
                (10, 6),
            ]
            if front
            else [
                (6, 4),
                (22, 4),
                (22, 6),
                (30, 6),
                (30, 10),
                (36, 10),
                (38, 14),
                (36, 22),
                (28, 26),
                (16, 26),
                (8, 22),
                (4, 14),
            ]
        )
        a.poly(pts, p["wing"], p["edge"], 2)
        a.line([(12, 12), (22, 14), (28, 14)], p["light"], 2)
        a.line([(12, 18), (22, 20)], p["shade"], 2)
    else:
        classic.wing(a, p, front)
    a.save(style, f"{palette}-wing-" + ("front" if front else "side"))


def clothes(style, view, sleep, outfit):
    a = Art(style, 120, 112)
    front = view == "front"
    dy = 12 if sleep else 0
    if outfit in wardrobe.UNIFORMS:
        wardrobe.uniform(a, view, sleep, outfit, pixel_body_points)

    elif outfit == "cape":
        if a.pixel:
            if front:
                a.poly(
                    [(38, 60 + dy), (30, 68 + dy), (22, 98), (38, 94), (46, 68 + dy)],
                    "#76536f",
                    "#4d3b54",
                    2,
                )
                a.poly(
                    [(80, 60 + dy), (90, 72 + dy), (98, 98), (82, 94)],
                    "#76536f",
                    "#4d3b54",
                    2,
                )
            else:
                a.poly(
                    [
                        (70, 60 + dy),
                        (54, 60 + dy),
                        (28, 78),
                        (16, 100),
                        (44, 96),
                        (78, 72 + dy),
                    ],
                    "#865c87",
                    "#4e405d",
                    2,
                )
                a.poly(
                    [(54, 66 + dy), (28, 92), (20, 98), (38, 94), (62, 72 + dy)],
                    "#b982a2",
                )
        else:
            if front:
                a.path(
                    f"M41 {60 + dy} Q25 69 24 98 Q31 92 41 95 L50 {64 + dy}",
                    a.gradient("cape", "#9b6c9c", "#654766"),
                    "#59435e",
                    1,
                )
                a.path(
                    f"M79 {60 + dy} Q95 70 97 98 Q88 92 80 95 L73 {65 + dy}",
                    "#785679",
                    "#59435e",
                    1,
                )
            else:
                a.path(
                    f"M72 {60 + dy} Q49 {56 + dy} 35 76 Q23 88 16 101 Q32 94 43 98 Q60 91 79 {72 + dy} Z",
                    a.gradient("cape", "#a779a4", "#70506f"),
                    "#5d4663",
                    1.1,
                )
                a.path(f"M53 {66 + dy * 0.5} Q35 80 23 96 Q39 88 55 87", "#bf8da7")
                a.path("M40 82 Q34 90 31 95", "none", "#80567f", 1)
    a.save(style, f"outfit-{outfit}-{view}" + ("-sleep" if sleep else ""))


def neckwear(style, view, outfit):
    a = Art(style, 64, 80)
    front = view == "front"
    cx = 30 if front else 34
    if outfit in wardrobe.UNIFORMS:
        wardrobe.neckwear(a, view, outfit)
        a.save(style, f"neck-{outfit}-{view}")
        return

    fill = {
        "scarf": "#cf5968",
        "sailor": "#f0ead5",
        "space": "#8eafb9",
        "cape": "#765171",
    }[outfit]
    if a.pixel:
        a.poly(
            [
                (cx - 12, 46),
                (cx + 10, 46),
                (cx + 12, 50),
                (cx + 8, 54),
                (cx - 8, 54),
                (cx - 12, 50),
            ],
            fill,
            "#86434d" if outfit == "scarf" else "#617076",
            2,
        )
        if outfit == "scarf":
            x = cx - 8 if front else cx - 14
            a.poly(
                [
                    (x, 50),
                    (x + 10, 50),
                    (x + 10, 76),
                    (x + 6, 76),
                    (x + 6, 78),
                    (x + 2, 78),
                    (x + 2, 76),
                    (x, 76),
                ],
                "#b7435b",
            )
            a.rect(x, 66, 10, 2, "#f1c681")
            a.rect(x, 70, 10, 2, "#f1c681")
        if outfit == "sailor":
            a.poly(
                [
                    (cx - 10, 48),
                    (cx, 58),
                    (cx + 10, 48),
                    (cx + 6, 48),
                    (cx, 52),
                    (cx - 6, 48),
                ],
                "#456b90",
            )
            a.rect(cx - 2, 54, 4, 18, "#cf5b66")
        if outfit == "space":
            a.rect(cx - 6, 50, 12, 2, "#f2f2dd")
        if outfit == "cape":
            a.rect(cx - 4, 48, 8, 6, "#efc86b")
            a.rect(cx - 2, 48, 2, 2, "#fff0b3")
    else:
        a.path(
            f"M{cx - 12} 47 Q{cx} 42 {cx + 12} 47 L{cx + 10} 52 Q{cx} 57 {cx - 11} 52 Z",
            a.gradient("neck", fill, "#ad3f58" if outfit == "scarf" else fill),
            "#9e4b5a" if outfit == "scarf" else "#65767a",
            0.8,
        )
        if outfit == "scarf":
            x = cx - 14 if not front else cx - 8
            a.path(
                f"M{x} 50 Q{x + 6} 52 {x + 11} 50 L{x + 12} 76 Q{x + 6} 79 {x + 1} 76 Z",
                "#bc455e",
                "#a43d54",
                0.8,
            )
            a.path(
                f"M{x + 2} 67 L{x + 10} 68 M{x + 2} 72 L{x + 10} 73",
                "none",
                "#efc98b",
                2,
            )
            for dx in (2, 5, 8):
                a.line([(x + dx, 76), (x + dx, 79)], "#bc455e", 1.6)
            a.path(f"M{cx - 9} 48 Q{cx} 51 {cx + 9} 48", "none", "#ec9191", 1.4)
        if outfit == "sailor":
            a.path(
                f"M{cx - 11} 47 L{cx} 58 L{cx + 11} 47 L{cx + 7} 47 L{cx} 53 L{cx - 7} 47 Z",
                "#456b90",
            )
            a.path(
                f"M{cx - 2} 54 L{cx + 3} 54 L{cx + 4} 71 L{cx} 74 L{cx - 3} 71 Z",
                "#d1616c",
            )
        if outfit == "space":
            a.path(f"M{cx - 7} 50 Q{cx} 53 {cx + 7} 50", "none", "#e7efe6", 1.5)
        if outfit == "cape":
            a.ellipse(
                cx - 3.5,
                47,
                7,
                7,
                a.gradient("gold", "#ffe8a4", "#d9a84b"),
                "#b78a42",
                0.7,
            )
    a.save(style, f"neck-{outfit}-{view}")


def pixel_wing_points(front):
    return (
        [
            (16, 4),
            (24, 4),
            (26, 8),
            (26, 18),
            (22, 18),
            (22, 24),
            (16, 28),
            (10, 28),
            (6, 24),
            (4, 18),
            (4, 10),
            (10, 6),
        ]
        if front
        else [
            (6, 4),
            (22, 4),
            (22, 6),
            (30, 6),
            (30, 10),
            (36, 10),
            (38, 14),
            (36, 22),
            (28, 26),
            (16, 26),
            (8, 22),
            (4, 14),
        ]
    )


def sleeve(style, view, outfit):
    a = Art(style, 40, 30)
    wardrobe.sleeve(a, view == "front", outfit, pixel_wing_points)
    a.save(style, f"sleeve-{outfit}-" + ("front" if view == "front" else "side"))


def hat(style, view, name):
    a = Art(style, 64, 32)
    front = view == "front"
    if name in wardrobe.NEW_HATS:
        wardrobe.hat(a, view, name)
        a.save(style, f"hat-{name}-{view}")
        return

    if a.pixel:
        if name == "wizard":
            a.poly(
                [(16, 26), (22, 18), (24, 10), (30, 6), (34, 14), (40, 20), (44, 26)],
                "#8070ba",
                "#493d70",
                2,
            )
            a.rect(14, 24, 34, 4, "#d8b76b")
            a.poly(
                [(6, 28), (14, 26), (48, 26), (58, 28), (56, 30), (8, 30)],
                "#5c4c8c",
                "#463963",
                2,
            )
            a.rect(28, 16, 4, 4, "#ffde89")
        elif name == "pirate":
            a.poly(
                [
                    (6, 26),
                    (10, 14),
                    (22, 18),
                    (30, 10),
                    (40, 18),
                    (54, 14),
                    (58, 26),
                    (50, 30),
                    (14, 30),
                ],
                "#343a4b",
                "#242d39",
                2,
            )
            a.line([(8, 26), (20, 26), (30, 28), (44, 26), (56, 26)], "#d1b580", 2)
            a.rect(28, 18, 8, 6, "#f4ecd4")
            a.rect(30, 20, 2, 2, "#343a4b")
            a.rect(34, 20, 2, 2, "#343a4b")
        elif name == "santa":
            a.poly(
                [
                    (14, 26),
                    (18, 14),
                    (28, 8),
                    (40, 8),
                    (46, 14),
                    (46, 22),
                    (40, 22),
                    (38, 16),
                    (32, 16),
                    (36, 26),
                ],
                "#d35368",
                "#a73d52",
                2,
            )
            a.rect(12, 26, 38, 6, "#fff2dc")
            a.rect(42, 18, 10, 8, "#fff2dc")
        elif name == "explorer":
            a.poly(
                [(16, 26), (18, 16), (24, 10), (40, 10), (46, 16), (48, 26)],
                "#d2af73",
                "#8f744e",
                2,
            )
            a.rect(18, 22, 28, 4, "#796044")
            a.poly(
                [(6, 28), (16, 26), (48, 26), (58, 28), (54, 30), (10, 30)],
                "#e2c58d",
                "#9b8054",
                2,
            )
        elif name == "chef":
            a.poly(
                [
                    (18, 30),
                    (18, 20),
                    (10, 18),
                    (8, 14),
                    (10, 8),
                    (18, 6),
                    (24, 8),
                    (26, 4),
                    (36, 4),
                    (42, 8),
                    (48, 8),
                    (52, 12),
                    (50, 18),
                    (44, 20),
                    (44, 30),
                ],
                "#fff5e5",
                "#b1b9b4",
                2,
            )
            a.rect(20, 26, 22, 4, "#d5ded6")
            a.rect(18, 12, 4, 4, "#ffffff")
        else:
            a.poly(
                [(12, 30), (12, 12), (22, 20), (32, 8), (42, 20), (52, 12), (52, 30)],
                "#efc65b",
                "#a87f38",
                2,
            )
            a.rect(14, 26, 36, 4, "#d49a3d")
            a.rect(28, 22, 6, 6, "#d45e78")
            a.rect(18, 24, 4, 4, "#6bb7ad")
            a.rect(42, 24, 4, 4, "#6bb7ad")
    else:
        if name == "wizard":
            a.path(
                "M16 27 Q23 17 27 6 Q29 3 32 8 Q36 16 46 27 Z",
                a.gradient("cap", "#a193cf", "#665292"),
                "#5b477f",
                1,
            )
            a.path("M17 24 Q31 28 45 24 L47 28 Q31 32 15 28 Z", "#dec789")
            a.ellipse(
                5, 26, 54, 5.5, a.gradient("rim", "#8975b3", "#514273"), "#554475", 0.8
            )
            a.poly(
                [
                    (29, 14),
                    (30, 16),
                    (33, 17),
                    (30, 18),
                    (29, 21),
                    (28, 18),
                    (25, 17),
                    (28, 16),
                ],
                "#ffe9ac",
            )
        elif name == "pirate":
            a.path(
                "M5 26 Q7 16 10 14 Q18 21 23 17 L31 10 L40 17 Q47 20 54 14 Q58 20 59 26 Q32 33 5 26",
                a.gradient("pirate", "#505264", "#2e3544"),
                "#272d3b",
                1,
            )
            a.path("M8 26 Q30 31 56 26", "none", "#d9c18c", 1.5)
            a.ellipse(27, 17, 9, 7, "#f1ead5")
            a.rect(29, 23, 5, 2, "#f1ead5", 0.5)
            a.ellipse(29, 19, 1.5, 2, "#3a3f4c")
            a.ellipse(33, 19, 1.5, 2, "#3a3f4c")
        elif name == "santa":
            a.path(
                "M14 27 Q15 12 27 9 Q42 3 46 14 L46 22 L40 22 Q42 12 32 15 L37 27",
                a.gradient("red", "#ec8c91", "#c74b64"),
                "#a94358",
                1,
            )
            a.path(
                "M12 27 Q31 23 49 27 L49 31 Q31 28 12 31 Z", "#fff3df", "#ddd3c0", 0.7
            )
            a.ellipse(40, 18, 12, 10, "#fff4e3", "#e2d9c8", 0.6)
        elif name == "explorer":
            a.path(
                "M16 27 L19 17 Q21 9 30 10 L38 10 Q45 11 47 27 Z",
                a.gradient("tan", "#e5c994", "#c29c61"),
                "#a08356",
                1,
            )
            a.path("M18 23 Q32 26 46 23 L47 27 Q31 31 17 27 Z", "#826749")
            a.ellipse(
                5, 26, 54, 5.5, a.gradient("brim", "#ecd5a5", "#c7a16a"), "#a68a5d", 0.8
            )
            a.path("M24 15 L25 21 M40 16 L39 21", "none", "#ae8c5a", 0.7)
        elif name == "chef":
            a.path(
                "M18 29 L18 19 C7 22 6 10 13 8 Q19 4 25 9 C25 0 38 1 41 8 Q49 5 53 12 Q56 21 45 21 L44 30 Z",
                a.gradient("chef", "#ffffff", "#e1e7df"),
                "#b2bcb8",
                1,
            )
            a.path("M19 26 Q31 29 44 26 L44 31 L19 31 Z", "#e8ece1", "#b5beba", 0.7)
            a.path("M26 13 L27 22 M38 13 L37 23", "none", "#d3ddd6", 0.8)
        else:
            a.path(
                "M12 29 L12 13 L22 21 L32 8 L42 21 L52 13 L51 29 Z",
                a.gradient("gold", "#ffe6a0", "#e5b449"),
                "#b18a40",
                1,
            )
            a.path(
                "M13 26 Q31 30 51 26 L51 30 Q30 32 13 30 Z", "#e6b34b", "#bd9144", 0.8
            )
            a.ellipse(28.5, 23, 7, 6, "#d76b87", "#b95873", 0.6)
            a.ellipse(18, 25, 4, 4, "#72bfb2")
            a.ellipse(43, 25, 4, 4, "#72bfb2")
    # Front brims are flatter, reflecting a different headwear projection.
    if front and name in ("explorer", "wizard"):
        a.line(
            [(12, 29), (50, 29)],
            "#efd59b" if name == "explorer" else "#a38ac6",
            1 if not a.pixel else 2,
        )
    a.save(style, f"hat-{name}-{view}")


HATS = ("wizard", "pirate", "santa", "explorer", "chef", "crown") + wardrobe.NEW_HATS
OUTFITS = ("scarf", "cape") + wardrobe.UNIFORMS

for style in ("vector", "pixel"):
    for palette, p in PALETTES.items():
        if style == "vector":
            p = dict(p)
            if palette == "yellow":
                p.update(
                    body="#f7cc55",
                    light="#fff2ae",
                    shade="#e2ad40",
                    edge="#ad803c",
                    head="#ffdc70",
                    headlight="#fff0b0",
                    headshade="#edbb51",
                    wing="#efbd4c",
                    breast="#ffe9a2",
                )
            if palette == "white":
                p.update(
                    body="#f1ebde",
                    shade="#d6cebc",
                    edge="#90988d",
                    head="#fcf7e8",
                    headshade="#e6deca",
                    wing="#e3ddcc",
                    breast="#fff9e9",
                )
        for view in VIEWS:
            for sleep in (False, True):
                body(style, palette, p, view, sleep)
            for covered in (False, True):
                head(style, palette, p, view, covered)
        for front in (False, True):
            wing(style, palette, p, front)
    for view in VIEWS:
        for state in ("open", "closed", "wide"):
            eyes(style, view, state)
        for outfit in wardrobe.UNIFORMS + ("cape",):
            for sleep in (False, True):
                clothes(style, view, sleep, outfit)
        for outfit in OUTFITS:
            neckwear(style, view, outfit)
        for name in HATS:
            hat(style, view, name)
    for outfit in wardrobe.UNIFORMS:
        for front in (False, True):
            sleeve(style, "front" if front else "side", outfit)
    a = Art(style, 20, 8)
    if a.pixel:
        a.poly(
            [(2, 0), (12, 0), (12, 2), (18, 2), (20, 4), (18, 6), (2, 6), (0, 4)],
            "#e8a04b",
            "#ac7236",
            2,
        )
        a.rect(4, 2, 10, 2, "#ffc875")
    else:
        classic.foot(a)
    a.save(style, "foot")
(OUT / "manifest.json").write_text(
    json.dumps(
        {
            "canvas": [120, 112],
            "pixelCanvas": [60, 56],
            "head": [64, 58],
            "hat": [64, 32],
            "neckwear": [64, 80],
            "headAnchors": {
                "side": [78, 64],
                "threeQuarter": [72, 64],
                "front": [60, 64],
            },
            "hatOffset": [-30, -66],
            "pixelHatOffset": [-30, -64],
            "neckwearOffset": [-30, -48],
            "hats": list(HATS),
            "outfits": list(OUTFITS),
            "uniforms": list(wardrobe.UNIFORMS),
        },
        indent=2,
    )
    + "\n"
)
print(
    "Generated",
    len(list(OUT.rglob("*.svg"))),
    "classic SVGs and",
    len(list(OUT.rglob("*.png"))),
    "pixel PNGs",
)
