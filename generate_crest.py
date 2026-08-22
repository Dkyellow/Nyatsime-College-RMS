"""Generate the Nyatsime College crest PNG used in printable/PDF report cards.

Run once:  python generate_crest.py
Output:    app/static/img/nyatsime-crest.png
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

S = 4
W, H = 200, 220
NAVY = (28, 52, 128, 255)
GOLD_LIGHT = (247, 201, 72, 255)
WHITE = (255, 255, 255, 255)
PAGE_GREY = (241, 244, 250, 255)
LINE_BLUE = (147, 165, 201, 255)
MAROON = (122, 31, 43, 255)
CREAM = (255, 243, 214, 255)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'app', 'static', 'img', 'nyatsime-crest.png')


def pt(x, y):
    return (x * S, y * S)


def cubic_points(p0, p1, p2, p3, steps=40):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        pts.append(pt(x, y))
    return pts


def shield_polygon(scale=1.0, cx=100, cy=110):
    def sc(p):
        return (cx + (p[0] - cx) * scale, cy + (p[1] - cy) * scale)
    pts = [(100, 8), (182, 34), (182, 112)]
    pts += cubic_points(sc((182, 112)), sc((182, 160)), sc((148, 192)), sc((100, 212)))
    pts += cubic_points(sc((100, 212)), sc((52, 192)), sc((18, 160)), sc((18, 112)))
    pts.append((18, 34))
    return [pt(x, y) for x, y in pts]


def star(cx, cy, outer, inner, points=5):
    pts = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = -math.pi / 2 + i * math.pi / points
        pts.append(pt(cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def load_font(size):
    size = int(size * S)
    for name in ['georgiab.ttf', 'timesbd.ttf', 'arialbd.ttf']:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    img = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.polygon(shield_polygon(1.0), fill=GOLD_LIGHT)
    d.polygon(shield_polygon(0.93), fill=NAVY)

    keyline = shield_polygon(0.84)
    d.line(keyline + [keyline[0]], fill=GOLD_LIGHT, width=int(2.5 * S), joint='curve')

    d.polygon(star(60, 60, 9 * S, 3.6 * S), fill=GOLD_LIGHT)
    d.polygon(star(140, 60, 9 * S, 3.6 * S), fill=GOLD_LIGHT)

    flame_outer = [
        (100, 42), (106, 53), (113, 64), (114, 72),
        (111, 82), (105, 88), (100, 89),
        (95, 88), (89, 82), (86, 72),
        (87, 64), (94, 53),
    ]
    d.polygon([pt(x, y) for x, y in flame_outer], fill=GOLD_LIGHT)
    flame_inner = [
        (100, 58), (104, 65), (106, 71), (103, 79), (100, 81),
        (97, 79), (94, 71), (96, 65),
    ]
    d.polygon([pt(x, y) for x, y in flame_inner], fill=CREAM)
    d.rounded_rectangle([pt(95, 92), pt(105, 108)], radius=3 * S, fill=GOLD_LIGHT)

    d.polygon([pt(98, 118), pt(48, 110), pt(48, 146), pt(98, 154)], fill=WHITE)
    d.polygon([pt(102, 118), pt(152, 110), pt(152, 146), pt(102, 154)], fill=PAGE_GREY)
    d.line([pt(56, 118), pt(94, 123)], fill=LINE_BLUE, width=S)
    d.line([pt(56, 128), pt(94, 133)], fill=LINE_BLUE, width=S)
    d.line([pt(144, 118), pt(106, 123)], fill=LINE_BLUE, width=S)
    d.line([pt(144, 128), pt(106, 133)], fill=LINE_BLUE, width=S)
    d.rounded_rectangle([pt(97.5, 112), pt(102.5, 158)], radius=2 * S, fill=MAROON)

    ribbon = [(38, 168), (162, 168), (156, 186), (44, 186)]
    d.polygon([pt(x, y) for x, y in ribbon], fill=GOLD_LIGHT)

    font = load_font(11)
    text = 'NYATSIME'
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((100 * S - tw / 2 - bbox[0], 176 * S - th / 2 - bbox[1]),
           text, font=font, fill=(19, 43, 102, 255))

    img = img.resize((W, H), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print('Saved', OUT)


if __name__ == '__main__':
    main()
