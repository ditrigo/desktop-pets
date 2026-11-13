"""Build-time convex contours of alpha; never shipped as executable code."""


def hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        return points

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    upper = []
    for p in points:
        while len(lower) > 1 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) > 1 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def alpha_hull(image, scale=1, offset=(0, 0)):
    alpha = image.getchannel("A")
    points = []
    for y in range(image.height):
        xs = [x for x in range(image.width) if alpha.getpixel((x, y)) > 32]
        if xs:
            lo, hi = xs[0], xs[-1] + 1
            points.extend([(lo, y), (hi, y), (lo, y + 1), (hi, y + 1)])
    return [
        [round(offset[0] + x * scale, 3), round(offset[1] + y * scale, 3)]
        for x, y in hull(points)
    ]
