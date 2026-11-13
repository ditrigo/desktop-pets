"""Original rounded duckling artwork, in the rig's logical coordinates."""


def body_shape(view, sleep):
    if view == "front":
        return (
            "M42 67 C48 59 73 59 80 68 C89 74 94 84 87 93 C78 105 43 105 33 94 C25 84 32 73 42 67 Z"
            if sleep
            else "M43 55 C51 49 70 49 78 56 C82 63 91 68 93 81 C96 96 81 103 61 103 C40 103 26 95 28 81 C29 69 39 62 43 55 Z"
        )
    if view == "threeQuarter":
        return (
            "M31 75 C39 64 68 61 82 72 C94 79 98 91 85 98 C71 106 39 104 27 94 C19 87 22 80 31 75 Z"
            if sleep
            else "M31 64 C37 54 50 51 65 52 C82 52 94 65 95 79 C97 94 82 103 59 103 C37 103 23 95 23 82 C22 75 25 68 31 64 Z"
        )
    return (
        "M28 76 C38 64 68 62 84 74 C97 83 96 94 82 99 C64 106 36 102 26 94 C18 87 20 81 28 76 Z"
        if sleep
        else "M29 65 C34 54 49 51 65 53 C83 54 95 65 95 80 C95 95 79 103 57 102 C35 102 21 94 21 81 C21 74 24 69 29 65 Z"
    )


def wing_shape(front):
    return (
        "M19 3 C10 2 5 9 5 17 C5 23 9 28 15 28 C23 28 29 20 28 12 C28 6 24 3 19 3 Z"
        if front
        else "M5 7 C11 2 23 3 32 8 C38 11 39 17 34 23 C29 28 20 29 13 25 C6 23 1 16 3 11 Q3 8 5 7 Z"
    )


def body(a, p, view, sleep):
    front = view == "front"
    dy = 12 if sleep else 0
    if not front:
        a.path(
            f"M31 {68 + dy} C20 {67 + dy} 13 {62 + dy} 12 {55 + dy} Q20 {55 + dy} 26 {61 + dy} Q26 {57 + dy} 30 {57 + dy} L39 {75 + dy} Z",
            p["shade"],
            p["edge"],
            1.5,
        )
        a.path(f"M17 {60 + dy} L29 {69 + dy}", "none", p["light"], 1.5)
    d = body_shape(view, sleep)
    a.path(d, a.gradient("body", p["light"], p["body"]), p["edge"], 1.65)
    a.begin_clip(d)
    a.path("M23 85 C37 102 78 104 94 83 L101 109 L19 109 Z", p["shade"])
    if front:
        a.ellipse(39, 65 + dy * 0.65, 43, 31 - dy * 0.6, p["breast"])
    else:
        a.ellipse(49, 67 + dy * 0.6, 37, 27 - dy * 0.5, p["breast"])
    if p["head"] == "#32866f":
        a.ellipse(
            46 if front else 72, 61 + dy, 31 if front else 19, 31 - dy * 0.6, "#92624b"
        )
    a.path(f"M33 {66 + dy} Q43 {57 + dy} 57 {58 + dy}", "none", p["light"], 3)
    a.end_clip()


def head(a, p, view, covered):
    front = view == "front"
    # A short neck and full cheeks keep the cap and collar on one head rig.
    a.path("M22 38 Q18 48 23 55 Q31 58 41 54 L40 38 Z", p["headshade"], p["edge"], 1.4)
    d = (
        "M8 28 C8 15 15 7 29 7 C44 7 52 16 52 29 C54 42 45 50 30 50 C15 50 6 42 8 28 Z"
        if front
        else "M9 28 C8 16 16 7 29 7 C43 6 51 15 51 28 C54 39 46 49 33 50 C18 52 7 43 8 32 Z"
    )
    a.path(d, a.gradient("head", p["headlight"], p["head"]), p["edge"], 1.55)
    a.path(
        "M10 35 Q16 48 33 47 Q45 47 50 35 C50 47 40 52 26 49 Q13 47 10 39 Z",
        p["headshade"],
    )
    a.path("M15 21 Q19 13 28 13", "none", p["headlight"], 3)
    if not covered:
        a.path(
            "M22 10 Q15 1 22 2 Q27 3 29 10 Q28 0 34 3 Q36 5 33 10",
            p["head"],
            p["edge"],
            1.3,
        )
    a.ellipse(12, 35, 9, 5, "#7fb3a2" if p["head"] == "#32866f" else "#f1b37b")
    if front:
        a.ellipse(41, 35, 8, 5, "#7fb3a2" if p["head"] == "#32866f" else "#f1b37b")
        a.path(
            "M18 35 Q29 30 43 35 Q48 39 42 44 Q29 49 18 43 Q13 39 18 35 Z",
            a.gradient("bill", "#ffca7c", "#e99843"),
            "#b47435",
            1.2,
        )
        a.path("M20 40 Q30 44 41 40", "none", "#c1843f", 1)
        a.ellipse(23, 35, 2, 1.5, "#a87538")
        a.ellipse(36, 35, 2, 1.5, "#a87538")
    else:
        a.path(
            "M44 33 Q51 31 59 33 Q66 35 62 40 Q56 46 45 43 Q41 40 44 33 Z",
            a.gradient("bill", "#ffce83", "#eca04a"),
            "#b47435",
            1.2,
        )
        a.path("M46 39 Q54 42 61 37", "none", "#bc7e37", 1)
        a.ellipse(51, 34, 2.4, 1.7, "#a87538")
    if p["head"] == "#32866f":
        a.path("M23 51 Q32 54 41 51", "none", "#f4eedb", 2.4)


def eyes(a, view, state):
    coords = (
        [(17, 22, 8), (36, 22, 8)]
        if view == "front"
        else [(20, 22, 5), (36, 22, 8)]
        if view == "threeQuarter"
        else [(35, 22, 8)]
    )
    for x, y, w in coords:
        if state == "closed":
            a.path(
                f"M{x} {y + 7} Q{x + w / 2} {y + 3} {x + w} {y + 7}",
                "none",
                "#354740",
                1.9,
            )
        else:
            h = 13 if state == "wide" else 10
            a.ellipse(x, y, w, h, "#273e38")
            a.ellipse(x + 1.2, y + 1.1, 2.7, 3.2, "#fffef0")
            a.ellipse(x + w - 2.4, y + h - 3, 1.2, 1.4, "#93b4a0")


def wing(a, p, front):
    a.path(
        wing_shape(front), a.gradient("wing", p["light"], p["wing"]), p["edge"], 1.45
    )
    a.path("M10 11 Q14 7 20 8" if front else "M8 10 Q17 6 26 11", "none", p["light"], 2)
    a.path(
        "M11 17 Q16 23 22 17" if front else "M10 17 Q20 24 30 17",
        "none",
        p["shade"],
        1.6,
    )


def foot(a):
    a.path(
        "M4 1 Q8 -1 11 2 L17 1 Q21 2 19 4 L18 6 Q9 9 2 6 Q-1 4 4 1 Z",
        a.gradient("foot", "#ffc77d", "#e69642"),
        "#b67938",
        1,
    )
    a.path("M8 3 L10 5 M14 3 L15 5", "none", "#ce873b", 0.8)
