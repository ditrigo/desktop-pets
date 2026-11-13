"""Fitted clothing and six new mix-and-match sets for both flat styles."""

from PIL import ImageChops
from classic import body_shape, wing_shape

NEW_HATS = ("rainhat", "detective", "beret", "straw", "tophat", "nightcap")
UNIFORMS = (
    "sailor",
    "space",
    "raincoat",
    "trench",
    "apron",
    "overalls",
    "tuxedo",
    "pajamas",
)
COLORS = {
    "sailor": ("#416b91", "#304c6b", "#f1ecdc"),
    "space": ("#c9dddf", "#79979f", "#557786"),
    "raincoat": ("#efbd48", "#b58432", "#fff0b1"),
    "trench": ("#c6a57d", "#8f7357", "#f1d9ad"),
    "apron": ("#e8e5d5", "#7b9690", "#34796c"),
    "overalls": ("#e6cda2", "#8e8169", "#4d7d9f"),
    "tuxedo": ("#344650", "#24333e", "#f6f0de"),
    "pajamas": ("#8d92c0", "#5e6592", "#e5d6a2"),
}


def clip_begin(a, d, name):
    a.begin_clip(d)


def star(a, x, y, color, size=3):
    a.poly(
        [
            (x, y - size),
            (x + 1, y - 1),
            (x + size, y),
            (x + 1, y + 1),
            (x, y + size),
            (x - 1, y + 1),
            (x - size, y),
            (x - 1, y - 1),
        ],
        color,
    )


def uniform(a, view, sleep, outfit, pixel_points):
    front = view == "front"
    fill, edge, trim = COLORS[outfit]
    if a.pixel:
        a.poly(pixel_points(view, sleep), fill, edge, 2)
        mask = a.image.getchannel("A")
    else:
        d = body_shape(view, sleep)
        a.path(d, a.gradient("fabric", fill, edge), edge, 1.5)
        clip_begin(a, d, "fabricClip")
    dy = 5 if sleep else 0
    chest = 60 if front else 83
    if outfit == "sailor":
        for yy in (90, 95):
            a.line([(30, yy), (44, yy + 4), (73, yy + 5), (89, yy - 1)], trim, 2)
        a.line(
            [(30, 64 + dy), (48, 58 + dy), (77, 60 + dy), (90, 69 + dy)], "#6f9cb7", 2
        )
    elif outfit == "space":
        x = chest - 10
        w = 20 if front else 12
        a.rect(x, 75 + dy, w, 15 - dy, trim, 2)
        a.rect(x + 2, 78 + dy, 6 if front else 4, 4, "#8dd1b5", 1)
        a.rect(x + w - 4, 78 + dy, 2, 4, "#efac75")
        a.line([(29, 92), (50, 97), (77, 96), (91, 87)], "#8cabaf", 3)
    elif outfit == "raincoat":
        a.line([(chest, 65 + dy), (chest, 98)], "#b68433", 2)
        for yy in (72, 82, 92):
            a.ellipse(chest - 4, yy + dy * 0.4, 3, 3, "#675f49")
        a.rect(36 if not front else 39, 81 + dy, 13, 10 - dy * 0.5, "#dba63b", 2)
        a.line(
            [(36 if not front else 39, 82 + dy), (49 if not front else 52, 82 + dy)],
            trim,
            2,
        )
        a.line([(30, 95), (48, 99), (76, 99), (89, 92)], trim, 2)
    elif outfit == "trench":
        a.line([(chest - 2, 65 + dy), (chest - 2, 99)], edge, 2)
        a.rect(25, 86 + dy * 0.3, 68, 5, "#92765d")
        a.rect(chest - 7, 85 + dy * 0.3, 9, 7, "#e7c88c", 1)
        a.rect(chest - 5, 87 + dy * 0.3, 5, 3, edge)
        for yy in (71, 78):
            for xx in (chest - 8, chest + 4):
                a.ellipse(xx, yy + dy, 2.5, 2.5, "#695b4c")
        a.line([(38, 80 + dy), (49, 78 + dy)], edge, 2)
    elif outfit in ("apron", "overalls"):
        if outfit == "apron":
            for yy in (62, 69, 76, 83):
                a.rect(24, yy + dy, 72, 2, "#aabbb0")
        denim = trim
        a.poly(
            [
                (chest - 17, 66 + dy),
                (chest + 11, 66 + dy),
                (chest + 15, 77 + dy),
                (93, 100),
                (29, 103),
                (36, 83 + dy),
                (chest - 17, 78 + dy),
            ],
            denim,
        )
        a.line([(chest - 14, 57 + dy), (chest - 12, 75 + dy)], denim, 5)
        a.line([(chest + 8, 57 + dy), (chest + 7, 75 + dy)], denim, 5)
        a.rect(
            chest - 13,
            78 + dy,
            19 if front else 13,
            11 - dy * 0.6,
            "#285f59" if outfit == "apron" else "#3d6688",
            2,
        )
        a.line(
            [(chest - 12, 80 + dy), (chest + 4 if front else chest - 1, 80 + dy)],
            "#adc8af" if outfit == "apron" else "#b7c5b8",
            1,
        )
        for xx in (chest - 13, chest + 7):
            a.ellipse(xx, 69 + dy, 3, 3, "#e8ca79")
        if outfit == "apron":
            for xx, yy, c in [
                (chest - 8, 83 + dy, "#e4a46d"),
                (chest - 3, 85 + dy, "#86b9c4"),
                (chest - 10, 88 + dy, "#e5cf74"),
            ]:
                a.rect(xx, yy, 3, 3, c, 1)
    elif outfit == "tuxedo":
        a.poly(
            [
                (chest - 13, 59 + dy),
                (chest + 10, 59 + dy),
                (chest + 3, 93),
                (chest - 4, 96),
            ],
            trim,
        )
        a.poly(
            [
                (chest - 16, 59 + dy),
                (chest - 6, 60 + dy),
                (chest - 4, 91),
                (chest - 16, 77 + dy),
                (chest - 10, 72 + dy),
                (chest - 19, 68 + dy),
            ],
            "#50646d",
        )
        a.poly(
            [
                (chest + 12, 59 + dy),
                (chest + 5, 61 + dy),
                (chest + 3, 90),
                (chest + 14, 76 + dy),
                (chest + 10, 71 + dy),
                (chest + 17, 67 + dy),
            ],
            "#50646d",
        )
        for yy in (75, 83, 90):
            a.ellipse(chest - 2, yy + dy * 0.3, 2.5, 2.5, "#53656b")
        a.poly(
            [(40, 73 + dy), (48, 73 + dy), (48, 78 + dy), (44, 76 + dy), (40, 78 + dy)],
            "#c26a76",
        )
    else:
        a.line([(chest, 63 + dy), (chest, 98)], "#d0c8dc", 2)
        for yy in (72, 83, 93):
            a.ellipse(chest - 4, yy + dy * 0.3, 2.5, 2.5, "#ede1bc")
        for xx, yy in [(37, 68), (54, 65), (38, 84), (58, 92), (78, 89)]:
            star(a, xx, yy + dy * 0.5, trim, 2.5)
        a.rect(43, 76 + dy, 13, 11 - dy * 0.5, "#7981b0", 2)
        a.line([(43, 78 + dy), (56, 78 + dy)], "#d9cee0", 2)
    if a.pixel:
        a.image.putalpha(ImageChops.multiply(a.image.getchannel("A"), mask))
    else:
        a.end_clip()


def neckwear(a, view, outfit):
    front = view == "front"
    cx = 30 if front else 34
    fill, edge, trim = COLORS[outfit]
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
            edge,
            2,
        )
    else:
        a.path(
            f"M{cx - 11} 47 Q{cx} 44 {cx + 11} 47 L{cx + 11} 52 Q{cx} 57 {cx - 11} 52 Z",
            fill,
            edge,
            1,
        )
    if outfit == "sailor":
        a.poly(
            [
                (cx - 12, 48),
                (cx, 61),
                (cx + 12, 48),
                (cx + 6, 48),
                (cx, 55),
                (cx - 6, 48),
            ],
            "#f6f0dc",
            edge,
            1.5,
        )
        a.poly(
            [(cx - 2, 56), (cx + 2, 56), (cx + 4, 72), (cx, 75), (cx - 3, 71)],
            "#c75b67",
        )
    elif outfit == "raincoat":
        a.poly(
            [(cx - 12, 47), (cx, 52), (cx - 7, 60), (cx - 14, 51)], "#ffdb73", edge, 1
        )
        a.poly(
            [(cx + 12, 47), (cx, 52), (cx + 7, 60), (cx + 14, 51)], "#ffdb73", edge, 1
        )
    elif outfit == "trench":
        a.poly(
            [(cx - 12, 47), (cx, 53), (cx - 5, 65), (cx - 14, 54)], "#eed6af", edge, 1
        )
        a.poly(
            [(cx + 12, 47), (cx, 53), (cx + 5, 65), (cx + 14, 54)], "#eed6af", edge, 1
        )
    elif outfit == "apron":
        a.poly(
            [(cx - 11, 48), (cx + 11, 48), (cx + 3, 57), (cx - 2, 59)],
            "#b96166",
            "#934f58",
            1,
        )
    elif outfit == "overalls":
        a.line([(cx - 10, 51), (cx + 10, 51)], "#f9e7c2", 2)
    elif outfit == "tuxedo":
        a.poly([(cx - 11, 48), (cx, 52), (cx - 7, 59)], trim)
        a.poly([(cx + 11, 48), (cx, 52), (cx + 7, 59)], trim)
        a.poly([(cx - 9, 52), (cx - 1, 55), (cx - 9, 59)], "#b75d72", "#83465b", 1)
        a.poly([(cx + 9, 52), (cx + 1, 55), (cx + 9, 59)], "#b75d72", "#83465b", 1)
        a.rect(cx - 2, 53, 4, 5, "#dc919b", 1)
    elif outfit == "pajamas":
        a.poly([(cx - 11, 48), (cx, 52), (cx - 6, 59), (cx - 12, 54)], "#e9e2d3")
        a.poly([(cx + 11, 48), (cx, 52), (cx + 6, 59), (cx + 12, 54)], "#e9e2d3")
    else:
        a.line([(cx - 9, 51), (cx + 9, 51)], "#f1efdb", 2)


def sleeve(a, front, outfit, pixel_points):
    fill, edge, trim = COLORS[outfit]
    if a.pixel:
        a.poly(pixel_points(front), "#ffffff")
        mask = a.image.getchannel("A")
        a.image.paste((0, 0, 0, 0), (0, 0, a.image.width, a.image.height))
    else:
        clip_begin(a, wing_shape(front), "sleeveClip")
    # Upper arm only: the feather tips remain visible when the wing lifts.
    a.poly([(1, 1), (34, 1), (34, 12), (22, 16), (5, 14)], fill)
    if outfit in ("apron", "overalls"):
        trim = "#a6b5a8" if outfit == "apron" else "#b69972"
    a.line([(4, 13), (20, 15), (31, 12)], trim, 2)
    if outfit == "pajamas":
        star(a, 18, 8, "#e5d6a2", 2)
    if a.pixel:
        a.image.putalpha(ImageChops.multiply(a.image.getchannel("A"), mask))
    else:
        a.end_clip()


def hat(a, view, name):
    front = view == "front"
    if name == "rainhat":
        if a.pixel:
            a.poly(
                [(16, 26), (18, 14), (24, 10), (40, 10), (46, 16), (48, 26)],
                "#edbf51",
                "#ab8234",
                2,
            )
            a.poly(
                [(6, 28), (16, 24), (48, 24), (58, 28), (54, 30), (10, 30)],
                "#ffda72",
                "#ab8234",
                2,
            )
        else:
            a.path(
                "M16 26 L19 15 Q21 9 30 10 L39 10 Q46 12 48 26 Z",
                a.gradient("rain", "#ffe08a", "#e3ac39"),
                "#aa823d",
                1.2,
            )
            a.path(
                "M16 24 Q32 28 48 24 L58 29 Q34 34 6 29 Z", "#f6cb60", "#aa823d", 1.2
            )
        a.line([(20, 21), (44, 21)], "#c49740", 2)
    elif name == "detective":
        if a.pixel:
            a.poly(
                [(10, 26), (16, 16), (24, 10), (38, 10), (48, 18), (52, 26)],
                "#bda17c",
                "#7e6954",
                2,
            )
        else:
            a.path(
                "M10 27 Q15 10 28 10 Q44 7 53 27 Z",
                a.gradient("tweed", "#d7bc94", "#ae906c"),
                "#7e6954",
                1.2,
            )
        for xx in (20, 28, 36, 44):
            a.line([(xx, 14), (xx, 26)], "#8f7b62", 1 if not a.pixel else 2)
        a.line([(15, 20), (48, 20)], "#e7cd9f", 2)
        a.poly(
            [(4, 28), (16, 25), (48, 25), (60, 28), (56, 30), (8, 30)],
            "#9b8265",
            "#75634f",
            1.5,
        )
    elif name == "beret":
        if a.pixel:
            a.poly(
                [
                    (10, 20),
                    (16, 12),
                    (26, 8),
                    (44, 8),
                    (54, 14),
                    (54, 22),
                    (46, 28),
                    (16, 28),
                ],
                "#b75d70",
                "#80465d",
                2,
            )
        else:
            a.path(
                "M11 25 C1 16 17 8 31 8 Q52 5 56 17 Q57 25 43 29 L18 29 Z",
                a.gradient("beret", "#d27b87", "#a34e67"),
                "#80465d",
                1.3,
            )
        a.rect(30, 4, 4, 6, "#80465d", 1)
        a.rect(16, 26, 32, 6, "#80465d", 1)
    elif name == "straw":
        if a.pixel:
            a.poly(
                [(18, 26), (20, 16), (26, 10), (40, 10), (46, 18), (46, 26)],
                "#ead09a",
                "#ac8c53",
                2,
            )
        else:
            a.path(
                "M17 26 L20 16 Q23 10 31 10 Q43 8 47 26 Z", "#ead09a", "#ac8c53", 1.2
            )
        for yy in (16, 20):
            a.line([(21, yy), (43, yy)], "#c3a16d", 1 if not a.pixel else 2)
        a.rect(18, 23, 29, 4, "#77916c")
        if a.pixel:
            a.poly(
                [(4, 28), (16, 26), (48, 26), (60, 28), (58, 30), (6, 30)],
                "#efdbab",
                "#ac8c53",
                2,
            )
        else:
            a.ellipse(3, 26, 58, 5, "#efdbab", "#ac8c53", 1)
        a.ellipse(43, 21, 6, 6, "#cf7f83")
        a.ellipse(45, 23, 2, 2, "#ffe0a0")
    elif name == "tophat":
        a.poly([(18, 26), (16, 6), (48, 6), (46, 26)], "#354751", "#21313b", 1.5)
        a.rect(19, 20, 27, 6, "#b9697d", 1)
        if a.pixel:
            a.poly(
                [(6, 28), (16, 26), (48, 26), (58, 28), (54, 30), (10, 30)],
                "#354751",
                "#21313b",
                2,
            )
        else:
            a.ellipse(5, 26, 54, 5, "#354751", "#21313b", 1.2)
        a.line([(22, 9), (22, 17)], "#74888f", 2)
    else:
        if a.pixel:
            a.poly(
                [
                    (14, 26),
                    (20, 16),
                    (32, 8),
                    (44, 10),
                    (50, 18),
                    (46, 22),
                    (42, 18),
                    (36, 16),
                    (40, 26),
                ],
                "#8e93c4",
                "#5b6494",
                2,
            )
        else:
            a.path(
                "M14 27 Q22 9 34 9 Q49 5 52 20 L45 23 Q42 15 34 16 L40 27 Z",
                a.gradient("night", "#b5b3dc", "#838bc1"),
                "#5b6494",
                1.2,
            )
        a.rect(12, 26, 38, 6, "#eee5d4", 1)
        a.ellipse(44, 19, 9, 8, "#eee5d4")
        star(a, 30, 19, "#f1dba3", 3)
    if front and name in ("rainhat", "straw", "detective", "tophat"):
        a.line(
            [(13, 29), (51, 29)],
            "#f3dcad" if name != "tophat" else "#72848c",
            1 if not a.pixel else 2,
        )
