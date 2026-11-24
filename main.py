#!/usr/bin/env python3
"""Draw a deterministic 1024x1024 newspaper front page summarising
24 November 2026 world news, written to /output/entry.png.

No network, no randomness: every run produces identical bytes.
"""

import os
import struct
import zlib

W = H = 1024
OUT = os.environ.get("ENTRY_OUT", "/output/entry.png")

# ---------------------------------------------------------------- palette
INK      = (18, 18, 22, 255)
PAPER    = (246, 242, 233, 255)
RED      = (178, 34, 34, 255)
BLUE     = (28, 60, 110, 255)
GOLD     = (196, 148, 40, 255)
GREEN    = (34, 98, 62, 255)
GREY     = (120, 118, 112, 255)
RULE     = (40, 40, 44, 255)

# ---------------------------------------------------------------- raster
buf = bytearray(PAPER * (W * H))

def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 4
        a = c[3] / 255.0
        buf[i]   = int(buf[i]   * (1 - a) + c[0] * a)
        buf[i+1] = int(buf[i+1] * (1 - a) + c[1] * a)
        buf[i+2] = int(buf[i+2] * (1 - a) + c[2] * a)
        buf[i+3] = 255

def rect(x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(H, y1)):
        base = (y * W + max(0, x0)) * 4
        n = (min(W, x1) - max(0, x0)) * 4
        a = c[3] / 255.0
        for k in range(0, n, 4):
            buf[base+k]   = int(buf[base+k]   * (1 - a) + c[0] * a)
            buf[base+k+1] = int(buf[base+k+1] * (1 - a) + c[1] * a)
            buf[base+k+2] = int(buf[base+k+2] * (1 - a) + c[2] * a)
            buf[base+k+3] = 255

def frame(x0, y0, x1, y1, c, t=1):
    rect(x0, y0, x1, y0 + t, c); rect(x0, y1 - t, x1, y1, c)
    rect(x0, y0, x0 + t, y1, c); rect(x1 - t, y0, x1, y1, c)

def line(x0, y0, x1, y1, c, t=1):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        for ox in range(t):
            for oy in range(t):
                px(x0 + ox, y0 + oy, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy: err -= dy; x0 += sx
        if e2 <  dx: err += dx; y0 += sy

def disc(cx, cy, r, c):
    for y in range(-r, r + 1):
        span = int((r * r - y * y) ** 0.5)
        rect(cx - span, cy + y, cx + span + 1, cy + y + 1, c)

def ring(cx, cy, r, c, t=2):
    for y in range(-r - t, r + t + 1):
        for x in range(-r - t, r + t + 1):
            d2 = x * x + y * y
            if (r - t) ** 2 <= d2 <= (r + t) ** 2:
                px(cx + x, cy + y, c)

def tri(p0, p1, p2, c):
    minx = min(p0[0], p1[0], p2[0]); maxx = max(p0[0], p1[0], p2[0])
    miny = min(p0[1], p1[1], p2[1]); maxy = max(p0[1], p1[1], p2[1])
    def s(a, b, p):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    d1, d2, d3 = s(p0, p1, (0, 0)), s(p1, p2, (0, 0)), s(p2, p0, (0, 0))
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    for y in range(miny, maxy + 1):
        for x in range(minx, maxx + 1):
            d1, d2, d3 = s(p0, p1, (x, y)), s(p1, p2, (x, y)), s(p2, p0, (x, y))
            neg = d1 < 0 or d2 < 0 or d3 < 0
            pos = d1 > 0 or d2 > 0 or d3 > 0
            if not (neg and pos):
                px(x, y, c)

# 5x7 bitmap font, glyphs for A-Z 0-9 punctuation
FONT = {
 'A':["01110","10001","10001","11111","10001","10001","10001"],
 'B':["11110","10001","10001","11110","10001","10001","11110"],
 'C':["01110","10001","10000","10000","10000","10001","01110"],
 'D':["11110","10001","10001","10001","10001","10001","11110"],
 'E':["11111","10000","10000","11110","10000","10000","11111"],
 'F':["11111","10000","10000","11110","10000","10000","10000"],
 'G':["01110","10001","10000","10111","10001","10001","01110"],
 'H':["10001","10001","10001","11111","10001","10001","10001"],
 'I':["11111","00100","00100","00100","00100","00100","11111"],
 'J':["00111","00010","00010","00010","00010","10010","01100"],
 'K':["10001","10010","10100","11000","10100","10010","10001"],
 'L':["10000","10000","10000","10000","10000","10000","11111"],
 'M':["10001","11011","10101","10101","10001","10001","10001"],
 'N':["10001","11001","10101","10011","10001","10001","10001"],
 'O':["01110","10001","10001","10001","10001","10001","01110"],
 'P':["11110","10001","10001","11110","10000","10000","10000"],
 'Q':["01110","10001","10001","10001","10101","10011","01111"],
 'R':["11110","10001","10001","11110","10100","10010","10001"],
 'S':["01111","10000","10000","01110","00001","00001","11110"],
 'T':["11111","00100","00100","00100","00100","00100","00100"],
 'U':["10001","10001","10001","10001","10001","10001","01110"],
 'V':["10001","10001","10001","10001","10001","01010","00100"],
 'W':["10001","10001","10001","10101","10101","11011","10001"],
 'X':["10001","10001","01010","00100","01010","10001","10001"],
 'Y':["10001","10001","01010","00100","00100","00100","00100"],
 'Z':["11111","00001","00010","00100","01000","10000","11111"],
 '0':["01110","10001","10011","10101","11001","10001","01110"],
 '1':["00100","01100","00100","00100","00100","00100","01110"],
 '2':["01110","10001","00001","00010","00100","01000","11111"],
 '3':["11110","00001","00001","01110","00001","00001","11110"],
 '4':["00010","00110","01010","10010","11111","00010","00010"],
 '5':["11111","10000","11110","00001","00001","10001","01110"],
 '6':["00110","01000","10000","11110","10001","10001","01110"],
 '7':["11111","00001","00010","00100","01000","01000","01000"],
 '8':["01110","10001","10001","01110","10001","10001","01110"],
 '9':["01110","10001","10001","01111","00001","00010","01100"],
 ' ':["00000"]*7,
 '.':["00000","00000","00000","00000","00000","00110","00110"],
 ',':["00000","00000","00000","00000","00110","00100","01000"],
 '-':["00000","00000","00000","11111","00000","00000","00000"],
 ':':["00000","00110","00110","00000","00110","00110","00000"],
 '/':["00001","00010","00010","00100","01000","01000","10000"],
 "'":["00100","00100","00000","00000","00000","00000","00000"],
 '!':["00100","00100","00100","00100","00100","00000","00100"],
 '%':["11001","11010","00010","00100","01000","01011","10011"],
 '(':["00010","00100","01000","01000","01000","00100","00010"],
 ')':["01000","00100","00010","00010","00010","00100","01000"],
 '+':["00000","00100","00100","11111","00100","00100","00000"],
 '=':["00000","00000","11111","00000","11111","00000","00000"],
}

def text(x, y, s, c, scale=1, spacing=1):
    cx = x
    for ch in s.upper():
        g = FONT.get(ch, FONT[' '])
        for gy, row in enumerate(g):
            for gx, bit in enumerate(row):
                if bit == '1':
                    rect(cx + gx * scale, y + gy * scale,
                         cx + gx * scale + scale, y + gy * scale + scale, c)
        cx += (5 * scale + spacing)

def text_w(s, scale=1, spacing=1):
    return len(s) * (5 * scale + spacing) - spacing

def text_center(cx, y, s, c, scale=1, spacing=1):
    text(cx - text_w(s, scale, spacing) // 2, y, s, c, scale, spacing)

def text_right(x, y, s, c, scale=1, spacing=1):
    text(x - text_w(s, scale, spacing), y, s, c, scale, spacing)

# ---------------------------------------------------------------- layout
M = 24                       # page margin
CW = W - 2 * M               # content width

def fake_lines(x, y, w, n, c, gap=8, scale=2):
    """Blocks of pseudo body text: grey bars of varying length."""
    lens = [1.0, 0.92, 0.97, 0.85, 1.0, 0.9, 0.95, 0.78, 1.0, 0.88]
    for i in range(n):
        lw = int(w * lens[i % len(lens)])
        rect(x, y + i * (5 * scale + gap), x + lw, y + i * (5 * scale + gap) + 5 * scale, c)

# ---- masthead band
rect(0, 0, W, 8, INK)
text(M, 26, "THE GLOBAL LEDGER", INK, scale=6, spacing=2)
text_right(W - M, 30, "VOL. LXXXII - NO. 47", GREY, scale=2)
text_right(W - M, 52, "EST. 1944", GREY, scale=2)
text(M, 58, "INTERNATIONAL EDITION", RED, scale=2)
rect(0, 92, W, 95, INK)

# ---- dateline bar
rect(0, 95, W, 130, INK)
text_center(W // 2, 104, "TUESDAY 24 NOVEMBER 2026", PAPER, scale=3, spacing=2)
rect(0, 130, W, 134, INK)

# ---- lead banner headline
y = 148
text(M, y, "WORLD AT THE CROSSROADS:", INK, scale=7, spacing=1)
y += 62
text(M, y, "CEASEFIRE, VOTES, STORMS", RED, scale=7, spacing=1)
y += 66
rect(M, y, W - M, y + 3, INK)

# ---- three-column news grid under the banner
GRID_TOP = y + 12
COL_W = (CW - 2 * 20) // 3
COL_X = [M, M + COL_W + 20, M + 2 * (COL_W + 20)]
PANEL_H = 300

def panel_head(i, s, c):
    x = COL_X[i]
    rect(x, GRID_TOP, x + COL_W, GRID_TOP + 34, c)
    text(x + 8, GRID_TOP + 11, s, PAPER, scale=2)

def panel_body(i, lines, kick=None):
    x = COL_X[i] + 6
    yy = GRID_TOP + 44
    if kick:
        text(x, yy, kick, RED, scale=2)
        yy += 20
    fake_lines(x, yy, COL_W - 16, lines, GREY)

# Column 1: conflict / ceasefire
panel_head(0, "CEASEFIRE HOLDS", RED)
gx, gy = COL_X[0] + COL_W // 2, GRID_TOP + 78
disc(gx, gy, 30, (230, 226, 214, 255))            # white dove silhouette
tri((gx - 34, gy + 34), (gx + 6, gy + 6), (gx - 34, gy + 6), (240, 238, 230, 255))
tri((gx + 4, gy + 6), (gx + 40, gy - 12), (gx + 4, gy - 4), (240, 238, 230, 255))
disc(gx + 6, gy - 8, 3, INK)
line(gx - 40, gy + 46, gx + 44, gy + 46, GREY, 2)
panel_body(0, 6, kick="DAY 9 OF TRUCE")

# Column 2: elections
panel_head(1, "VOTERS DECIDE", BLUE)
bx, by = COL_X[1] + COL_W // 2 - 30, GRID_TOP + 62
rect(bx, by, bx + 60, by + 44, BLUE)              # ballot box
rect(bx + 18, by - 6, bx + 42, by, INK)
rect(bx + 22, by - 30, bx + 46, by - 8, GOLD)     # ballot sliding in
tri((bx + 62, by + 10), (bx + 62, by + 44), (bx + 96, by + 27), BLUE)
line(bx + 84, by + 2, bx + 96, by + 14, GREEN, 3)
line(bx + 96, by + 14, bx + 116, by - 12, GREEN, 3)
panel_body(1, 6, kick="TURNOUT AT RECORD 71%")

# Column 3: climate
panel_head(2, "STORM SEASON", GREEN)
sx, sy = COL_X[2] + COL_W // 2, GRID_TOP + 70
disc(sx, sy + 24, 22, GREY)                        # swirling storm cell
disc(sx - 14, sy + 8, 12, (90, 88, 84, 255))
disc(sx + 12, sy + 12, 10, (90, 88, 84, 255))
for k in range(5):                                 # rain strokes
    line(sx - 28 + k * 14, sy + 40, sx - 34 + k * 14, sy + 60, BLUE, 2)
tri((sx + 26, sy - 34), (sx + 26, sy + 2), (sx - 6, sy + 2), GOLD)  # thermometer spike
rect(sx + 22, sy + 2, sx + 30, sy + 22, RED)
panel_body(2, 6, kick="'HOTTEST NOVEMBER ON RECORD'")

frame(M, GRID_TOP - 4, W - M, GRID_TOP + PANEL_H + 4, RULE, 2)

# ---- mid-page feature strip: markets + tech
MID = GRID_TOP + PANEL_H + 18
rect(M, MID, W - M, MID + 150, INK)
text(M + 16, MID + 14, "MARKETS & TECH", GOLD, scale=3, spacing=1)
seps = [M + 250, M + 500, M + 750]
for s_ in seps:
    rect(s_, MID + 10, s_ + 1, MID + 140, (70, 70, 76, 255))
# index sparkline up
rect(seps[0] + 16, MID + 60, seps[0] + 216, MID + 62, GOLD)
pts = [(0, 40), (25, 30), (50, 34), (75, 18), (100, 24), (125, 8), (150, 14), (175, 0)]
for (ax, ay), (bx2, by2) in zip(pts, pts[1:]):
    line(seps[0] + 16 + ax, MID + 130 - 40 - ay, seps[0] + 16 + bx2, MID + 130 - 40 - by2, GREEN, 3)
text(seps[0] + 16, MID + 96, "+2.4%  GLOBAL 500", PAPER, scale=2)
text(seps[0] + 16, MID + 120, "OIL -3.1%  GOLD +1.2%", GREY, scale=2)
# silicon wafer / chip
cx, cy = seps[1] + 100, MID + 78
rect(cx - 34, cy - 34, cx + 34, cy + 34, (60, 62, 80, 255))
rect(cx - 22, cy - 22, cx + 22, cy + 22, GOLD)
for k in range(4):
    line(cx - 34, cy - 24 + k * 16, cx - 46, cy - 24 + k * 16, (120, 122, 140, 255), 3)
    line(cx + 34, cy - 24 + k * 16, cx + 46, cy - 24 + k * 16, (120, 122, 140, 255), 3)
    line(cx - 24 + k * 16, cy - 34, cx - 24 + k * 16, cy - 46, (120, 122, 140, 255), 3)
    line(cx - 24 + k * 16, cy + 34, cx - 24 + k * 16, cy + 46, (120, 122, 140, 255), 3)
text(seps[1] + 16, MID + 118, "AI CHIP EXPORT PACT SIGNED", PAPER, scale=2)
# rocket / space
rx, ry = seps[2] + 100, MID + 76
tri((rx, ry - 34), (rx - 14, ry + 6), (rx + 14, ry + 6), PAPER)
rect(rx - 14, ry + 6, rx + 14, ry + 26, RED)
tri((rx - 14, ry + 26), (rx - 26, ry + 40), (rx - 14, ry + 40), GOLD)
tri((rx + 14, ry + 26), (rx + 14, ry + 40), (rx + 26, ry + 40), GOLD)
disc(rx, ry - 10, 5, BLUE)
rect(rx - 8, ry + 44, rx + 8, ry + 58, GOLD)
rect(rx - 4, ry + 58, rx + 4, ry + 66, RED)
text(seps[2] + 16, MID + 118, "CREW MISSION DOCKS STATION", PAPER, scale=2)

# ---- lower half: two feature panels
LOW = MID + 164
HALF_W = (CW - 20) // 2
# left: globe / diplomacy
rect(M, LOW, M + HALF_W, LOW + 170, (232, 228, 216, 255))
gx2, gy2 = M + 90, LOW + 85
ring(gx2, gy2, 56, BLUE, 3)
line(gx2 - 56, gy2, gx2 + 56, gy2, BLUE, 2)
line(gx2, gy2 - 56, gx2, gy2 + 56, BLUE, 2)
for k in (20, 40):
    line(gx2 - 52, gy2 - k, gx2 + 52, gy2 - k, BLUE, 1)
    line(gx2 - 52, gy2 + k, gx2 + 52, gy2 + k, BLUE, 1)
disc(gx2 - 20, gy2 - 24, 6, RED)
disc(gx2 + 26, gy2 + 18, 5, RED)
disc(gx2 + 8, gy2 - 34, 4, RED)
text(M + 170, LOW + 24, "SUMMIT OF 40 NATIONS", INK, scale=3)
fake_lines(M + 170, LOW + 66, HALF_W - 190, 6, GREY)
frame(M, LOW, M + HALF_W, LOW + 170, RULE, 2)
# right: energy / wind turbines
rect(M + HALF_W + 20, LOW, W - M, LOW + 170, (232, 228, 216, 255))
for bx3, bh in ((M + HALF_W + 70, 90), (M + HALF_W + 130, 110), (M + HALF_W + 190, 84)):
    line(bx3, LOW + 150, bx3, LOW + 150 - bh, GREEN, 4)
    for ang in (30, 150, 270):
        import math
        ex = bx3 + int(26 * math.cos(math.radians(ang)))
        ey = LOW + 150 - bh + int(26 * math.sin(math.radians(ang)))
        line(bx3, LOW + 150 - bh, ex, ey, GREEN, 3)
text(M + HALF_W + 30, LOW + 24, "GRID GOES 60% RENEWABLE", INK, scale=2, spacing=1)
fake_lines(M + HALF_W + 230, LOW + 60, HALF_W - 230, 6, GREY)
frame(M + HALF_W + 20, LOW, W - M, LOW + 170, RULE, 2)

# ---- footer ticker
FOOT = LOW + 184
rect(0, FOOT, W, H, INK)
ticker = "ALSO TODAY: PEACE TALKS RESUME - STOCKS CLOSE HIGHER - WILDFIRES CONTAINED - NEW VACCINE APPROVED - METEOR SHOWER TONIGHT "
text(M, FOOT + 14, ticker[:58], PAPER, scale=2, spacing=1)
text(M, FOOT + 40, ticker[58:].rstrip() + " - END OF EDITION", GOLD, scale=2, spacing=1)
text_right(W - M, FOOT + 40, "PAGE 1 OF 1", GREY, scale=2)

# ---------------------------------------------------------------- encode
raw = b"".join(b"\x00" + bytes(buf[y * W * 4:(y + 1) * W * 4]) for y in range(H))

def chunk(tag, data):
    c = tag + data
    return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw, 9))
       + chunk(b"IEND", b""))

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "wb") as f:
    f.write(png)

size = len(png)
assert size <= 1048576, f"entry.png exceeds 1 MiB ({size} bytes)"
print(f"wrote {OUT}: {W}x{H}, {size} bytes")