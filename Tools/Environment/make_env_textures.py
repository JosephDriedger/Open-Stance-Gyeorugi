"""Procedural textures for the sparring venues (competition arena, training dojang).

    py Tools/Environment/make_env_textures.py

Writes PNGs to Resources/Environment/Textures. Everything is generated, so no third-party
images end up in the game. References: Resources/Images/FightingRing_Ref.png, TrainingDojang_Ref.png.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Resources", "Environment", "Textures")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)
FONT_BOLD = r"C:\Windows\Fonts\bahnschrift.ttf"


def save(img, name):
    path = os.path.join(OUT, name + ".png")
    img.save(path)
    print("wrote", path)


def value_noise(size, cells, octaves=4):
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = cells * 2 ** o
        grid = rng.random((n + 1, n + 1)).astype(np.float32)
        grid[-1, :] = grid[0, :]
        grid[:, -1] = grid[:, 0]
        img = Image.fromarray((grid * 255).astype(np.uint8)).resize((size + size // n, size + size // n), Image.BICUBIC)
        out += np.asarray(img, np.float32)[:size, :size] / 255.0 * amp
        total += amp
        amp *= 0.5
    return out / total


def height_to_normal(h, strength):
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))


# --- interlocking EVA mat tile, 1 m (1024 px): jigsaw seam on each edge + fine diamond emboss ---
S = 1024
y, x = np.mgrid[0:S, 0:S].astype(np.float32)
h = np.ones((S, S), np.float32)
# diamond emboss (the "straw" texture of taekwondo puzzle mats)
d = (np.abs(((x + y) % 24) - 12) + np.abs(((x - y) % 24) - 12)) / 24.0
h -= 0.08 * (d > 0.85)


def seam_offset(t):
    # dovetail teeth along a seam: 8 teeth per metre
    phase = (t / S * 8.0) % 1.0
    return np.where(phase < 0.5, 18.0, -18.0) * (np.abs(phase - 0.5) > 0.1) + 0.0


for axis in (0, 1):
    along = x if axis == 0 else y
    across = y if axis == 0 else x
    off = seam_offset(along)
    dist = np.minimum(np.abs(across - (22 + off)), np.abs(across - (S - 22 + off)))
    dist = np.minimum(dist, np.abs(across + S - (S - 22 + off)))
    h -= 0.55 * np.clip(1.0 - dist / 3.0, 0, 1)
h = np.clip(h, 0, 1)
save(height_to_normal(h, 6.0), "T_MatTile_N")
save(Image.fromarray((h * 255).astype(np.uint8)), "T_MatTile_H")

# --- detail textures (grayscale, multiplied with a colour in the material) ---
n = value_noise(1024, 8)
concrete = 0.78 + 0.22 * n + 0.05 * (rng.random((1024, 1024)) - 0.5)
save(Image.fromarray((np.clip(concrete, 0, 1) * 255).astype(np.uint8)), "T_Concrete_D")

plaster = 0.92 + 0.08 * value_noise(1024, 16, 3)
save(Image.fromarray((np.clip(plaster, 0, 1) * 255).astype(np.uint8)), "T_Plaster_D")

grain = np.zeros((1024, 1024), np.float32)
for i in range(6):   # planks 1024/6 px wide, vertical grain
    x0, x1 = i * 1024 // 6, (i + 1) * 1024 // 6
    tone = 0.85 + 0.15 * rng.random()
    stripes = 0.5 + 0.5 * np.sin((x[:, x0:x1] * 0.35 + 6 * value_noise(1024, 3, 2)[:, x0:x1]) + rng.random() * 6)
    grain[:, x0:x1] = tone * (0.88 + 0.12 * stripes)
    grain[:, x0:x0 + 2] *= 0.7
save(Image.fromarray((np.clip(grain, 0, 1) * 255).astype(np.uint8)), "T_Wood_D")

# --- Taegukgi (flag of the Republic of Korea), 3:2, proportions per the official specification ---
W, H = 1500, 1000
flag = Image.new("RGB", (W, H), (255, 255, 255))
dr = ImageDraw.Draw(flag)
RED, BLUE, BLACK = (205, 46, 58), (0, 71, 160), (0, 0, 0)
cx, cy, R = W / 2, H / 2, H / 4   # taeguk diameter = 1/2 flag height
# taeguk: red top, blue bottom, rotated along the flag diagonal
ang = math.degrees(math.atan2(2, 3))
tg = Image.new("RGBA", (int(2 * R) + 4, int(2 * R) + 4), (0, 0, 0, 0))
td = ImageDraw.Draw(tg)
c = R + 2
td.pieslice([c - R, c - R, c + R, c + R], 180, 360, fill=RED)
td.pieslice([c - R, c - R, c + R, c + R], 0, 180, fill=BLUE)
td.ellipse([c - R, c - R / 2, c, c + R / 2], fill=RED)
td.ellipse([c, c - R / 2, c + R, c + R / 2], fill=BLUE)
tg = tg.rotate(ang, resample=Image.BICUBIC)
flag.paste(tg, (int(cx - c), int(cy - c)), tg)
# trigrams: bar length = H/2 * ... use standard: each trigram 1/2 of taeguk radius wide
bar_w, bar_h, gap = H / 4, H / 24, H / 48


def trigram(center, angle_deg, pattern):
    # pattern: 3 strings, each "1" (solid) or "0" (broken), from inner to outer
    img = Image.new("RGBA", (int(bar_w * 1.2), int(bar_w * 1.2)), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(img)
    ox, oy = img.width / 2, img.height / 2
    total = 3 * bar_h + 2 * gap
    for i, p in enumerate(pattern):
        top = oy - total / 2 + i * (bar_h + gap)
        if p == "1":
            d2.rectangle([ox - bar_w / 2, top, ox + bar_w / 2, top + bar_h], fill=BLACK)
        else:
            half = (bar_w - gap) / 2
            d2.rectangle([ox - bar_w / 2, top, ox - bar_w / 2 + half, top + bar_h], fill=BLACK)
            d2.rectangle([ox + bar_w / 2 - half, top, ox + bar_w / 2, top + bar_h], fill=BLACK)
    img = img.rotate(angle_deg, resample=Image.BICUBIC, expand=False)
    flag.paste(img, (int(center[0] - img.width / 2), int(center[1] - img.height / 2)), img)


dist = R + H / 8 + bar_w / 2 * 0.2
for quadrant, pattern in ((( -1, -1), "111"), ((1, 1), "000"), ((1, -1), "010"), ((-1, 1), "101")):
    sx, sy = quadrant
    vx, vy = sx * 3, sy * 2
    L = math.hypot(vx, vy)
    pos = (cx + vx / L * (R + H / 6), cy + vy / L * (R + H / 6))
    rot = -math.degrees(math.atan2(vy, vx)) + 90
    trigram(pos, rot, pattern)
save(flag, "T_Taegukgi")

# --- dojang banner: navy side-kick silhouette with red/navy stripes ---
ban = Image.new("RGB", (1200, 900), (246, 246, 244))
bd = ImageDraw.Draw(ban)
NAVY = (22, 34, 84)
bd.polygon([(560, 330), (700, 300), (1080, 170), (1100, 210), (720, 370), (650, 420)], fill=NAVY)   # kicking leg
bd.polygon([(560, 330), (650, 420), (560, 640), (600, 860), (540, 870), (480, 640), (500, 420)], fill=NAVY)  # torso + standing leg
bd.ellipse([470, 200, 560, 290], fill=NAVY)                                                          # head
bd.polygon([(520, 330), (380, 420), (360, 400), (500, 300)], fill=NAVY)                              # arm
bd.polygon([(1180, 880), (1180, 600), (900, 880)], fill=(200, 30, 45))
bd.polygon([(1180, 560), (1180, 480), (820, 880), (740, 880)], fill=NAVY)
save(ban, "T_BannerKicker")

stripes = Image.new("RGB", (1200, 900), (246, 246, 244))
sd = ImageDraw.Draw(stripes)
for i, col in enumerate([(200, 30, 45), NAVY, (200, 30, 45)]):
    off = i * 170
    sd.polygon([(260 + off, 820), (520 + off, 820), (980 + off, 80), (720 + off, 80)], fill=col)
save(stripes, "T_BannerStripes")

# --- scoreboard screen: Chung (blue) 0 | 02:00 | Hong (red) 0 ---
sb = Image.new("RGB", (1600, 640), (10, 10, 12))
sbd = ImageDraw.Draw(sb)
sbd.rectangle([30, 40, 560, 600], fill=(20, 80, 200))
sbd.rectangle([1040, 40, 1570, 600], fill=(205, 30, 40))
big = ImageFont.truetype(FONT_BOLD, 360)
mid = ImageFont.truetype(FONT_BOLD, 150)
small = ImageFont.truetype(FONT_BOLD, 56)
for (x0, x1), txt in (((30, 560), "0"), ((1040, 1570), "0")):
    bb = sbd.textbbox((0, 0), txt, font=big)
    sbd.text(((x0 + x1 - (bb[2] - bb[0])) / 2 - bb[0], 320 - (bb[3] - bb[1]) / 2 - bb[1]), txt, fill="white", font=big)
bb = sbd.textbbox((0, 0), "02:00", font=mid)
sbd.text((800 - (bb[2] - bb[0]) / 2 - bb[0], 320 - (bb[3] - bb[1]) / 2 - bb[1]), "02:00", fill="white", font=mid)
for x0, label in ((30, "CHUNG"), (1040, "HONG")):
    sbd.text((x0 + 30, 520), label, fill=(235, 235, 235), font=small)
sbd.text((700, 470), "ROUND 1", fill=(200, 200, 200), font=small)
save(sb, "T_Scoreboard")

# --- exit sign ---
ex = Image.new("RGB", (512, 256), (20, 150, 70))
exd = ImageDraw.Draw(ex)
f = ImageFont.truetype(FONT_BOLD, 120)
bb = exd.textbbox((0, 0), "EXIT", font=f)
exd.text(((512 - (bb[2] - bb[0])) / 2 - bb[0], (256 - (bb[3] - bb[1])) / 2 - bb[1]), "EXIT", fill="white", font=f)
save(ex, "T_ExitSign")

# --- window view: out-of-focus autumn street (sky, buildings, orange trees) ---
V = 1024
view = Image.new("RGB", (V * 2, V), (0, 0, 0))
va = np.zeros((V, V * 2, 3), np.float32)
t = np.linspace(0, 1, V)[:, None]
va[:] = (np.array([0.62, 0.78, 0.95]) * (1 - t) + np.array([0.95, 0.88, 0.75]) * t)[:, None, :] if False else 0
sky_top, sky_bot = np.array([0.55, 0.72, 0.93]), np.array([0.96, 0.90, 0.78])
va[:] = (sky_top * (1 - t) + sky_bot * t)[:, None, :]
view = Image.fromarray((va * 255).astype(np.uint8))
vd = ImageDraw.Draw(view)
x0 = 0
while x0 < V * 2:
    w = int(rng.integers(120, 320))
    top = int(rng.integers(120, 520))
    shade = int(rng.integers(150, 205))
    col = (shade, shade - 8, shade - 20)
    vd.rectangle([x0, top, x0 + w, V], fill=col)
    for wy in range(top + 30, V - 60, 60):
        for wx in range(x0 + 20, x0 + w - 30, 50):
            vd.rectangle([wx, wy, wx + 26, wy + 32], fill=(shade - 50, shade - 45, shade - 35))
    x0 += w + int(rng.integers(0, 40))
for _ in range(90):
    cx_, cy_ = rng.integers(0, V * 2), rng.integers(420, 1000)
    r_ = int(rng.integers(50, 150))
    col = [(222, 136, 40), (240, 170, 60), (190, 90, 30), (230, 190, 90), (120, 140, 60)][int(rng.integers(0, 5))]
    vd.ellipse([cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_], fill=col)
vd.rectangle([0, V - 70, V * 2, V], fill=(120, 115, 110))
view = view.filter(ImageFilter.GaussianBlur(9))
save(view, "T_WindowView")


# =====================================================================================================
# Career venues (GDD 6.2): club dojang, school gym, provincial hall, national and continental arenas,
# world-final stage. A separate generator keeps the textures above byte-identical. These are drawn at
# their real aspect and resampled to power-of-two sizes so Unreal builds mips (the mesh restores the aspect).
# =====================================================================================================
vrng = np.random.default_rng(11)
NAVY_D, RED_HONG, BLUE_CHUNG, GOLD = (14, 22, 52), (200, 16, 46), (20, 80, 200), (212, 175, 90)


def font(size, path=FONT_BOLD):
    return ImageFont.truetype(path, size)


def save_pot(img, name, size):
    save(img.resize(size, Image.LANCZOS), name)


def centred(draw, box, text, fnt, fill):
    x0, y0, x1, y1 = box
    bb = draw.textbbox((0, 0), text, font=fnt)
    draw.text(((x0 + x1 - (bb[2] - bb[0])) / 2 - bb[0], (y0 + y1 - (bb[3] - bb[1])) / 2 - bb[1]), text, fill=fill, font=fnt)


def fit_font(draw, text, max_w, start, path=FONT_BOLD):
    s = start
    while s > 10:
        f_ = font(s, path)
        bb = draw.textbbox((0, 0), text, font=f_)
        if bb[2] - bb[0] <= max_w:
            return f_
        s -= 4
    return font(10, path)


def kicker_mark(size, colour):
    """The side-kick silhouette from T_BannerKicker as an RGBA stamp."""
    m = Image.new("RGBA", (1200, 900), (0, 0, 0, 0))
    md = ImageDraw.Draw(m)
    md.polygon([(560, 330), (700, 300), (1080, 170), (1100, 210), (720, 370), (650, 420)], fill=colour)
    md.polygon([(560, 330), (650, 420), (560, 640), (600, 860), (540, 870), (480, 640), (500, 420)], fill=colour)
    md.ellipse([470, 200, 560, 290], fill=colour)
    md.polygon([(520, 330), (380, 420), (360, 400), (500, 300)], fill=colour)
    m = m.crop(m.getbbox())
    k = size / max(m.size)
    return m.resize((int(m.width * k), int(m.height * k)), Image.LANCZOS)


# --- school gym floor: maple planks with basketball (FIBA 28 x 15 m) and volleyball (18 x 9 m) lines ---
# 4096 px = 36 m square, centred on the court; U along +X (court length), V along +Y.
G, GM = 4096, 36.0
PPM = G / GM
gy, gx = np.mgrid[0:G, 0:G].astype(np.float32)
plank_w = 0.07 * PPM
row = (gy / plank_w).astype(np.int64)
offset = (row * 7919 % 97) / 97.0 * 2.4 * PPM          # staggered butt joints, 2.4 m boards
board = ((gx + offset) / (2.4 * PPM)).astype(np.int64)
seed_tone = ((row * 73856093) ^ (board * 19349663)) % 1000 / 1000.0
tone = 0.9 + 0.1 * seed_tone
streak = 0.96 + 0.04 * np.sin(gx * 0.05 + seed_tone * 40 + np.sin(gy * 0.3) * 2)
wood = np.stack([226 * tone * streak, 182 * tone * streak, 124 * tone * streak], -1)
seam = ((gy % plank_w) < 1.2) | (((gx + offset) % (2.4 * PPM)) < 1.5)
wood[seam] *= 0.82
court = Image.fromarray(np.clip(wood, 0, 255).astype(np.uint8))
cd = ImageDraw.Draw(court)
del gy, gx, row, offset, board, seed_tone, tone, streak, wood, seam


def P(x, y):
    """Court metres (origin at centre, +Y towards the top of the image) to pixels."""
    return (G / 2 + x * PPM, G / 2 - y * PPM)


GREEN, LINE, VB = (28, 84, 58), (250, 250, 246), (232, 196, 40)
LW = 0.05 * PPM


def box_px(x0, y0, x1, y1):
    (ax, ay), (bx_, by_) = P(x0, y0), P(x1, y1)
    return [min(ax, bx_), min(ay, by_), max(ax, bx_), max(ay, by_)]


# painted keys and the out-of-bounds band in the school colour, lines on top
for s in (-1, 1):
    cd.rectangle(box_px(s * 14.0, 2.45, s * 8.2, -2.45), fill=GREEN)
for x0, y0, x1, y1 in ((-16, 9.5, 16, 7.5), (-16, -7.5, 16, -9.5), (-16, 7.5, -14, -7.5), (14, 7.5, 16, -7.5)):
    cd.rectangle(box_px(x0, y0, x1, y1), fill=GREEN)


def line_rect(x0, y0, x1, y1, col=LINE, w=LW):
    cd.rectangle(box_px(x0, y0, x1, y1), outline=col, width=int(w))


def arc(cx, cy, r, a0, a1, col=LINE, w=LW):
    cd.arc(box_px(cx - r, cy + r, cx + r, cy - r), a0, a1, fill=col, width=int(w))


line_rect(-14, 7.5, 14, -7.5)
cd.rectangle(box_px(-0.025, 7.5, 0.025, -7.5), fill=LINE)
arc(0, 0, 1.8, 0, 360)
for s in (-1, 1):
    bx = s * (14.0 - 1.575)                               # basket centre
    line_rect(s * 14, 2.45, s * 8.2, -2.45)
    arc(s * 8.2, 0, 1.8, 0, 360)
    # three-point line: straight parts 0.9 m in from the sidelines, arc r = 6.75 m
    yl = 7.5 - 0.9
    ang = math.degrees(math.asin(yl / 6.75))
    xa = bx - s * math.sqrt(6.75 ** 2 - yl ** 2)
    for yy in (yl, -yl):
        cd.rectangle(box_px(s * 14, yy + 0.025, xa, yy - 0.025), fill=LINE)
    if s > 0:
        arc(bx, 0, 6.75, 180 - ang, 180 + ang)
    else:
        arc(bx, 0, 6.75, -ang, ang)
# volleyball court (yellow), centred
line_rect(-9, 4.5, 9, -4.5, VB, LW * 0.9)
for xx in (-3, 0, 3):
    cd.rectangle(box_px(xx - 0.025, 4.5, xx + 0.025, -4.5), fill=VB)
court = court.filter(ImageFilter.GaussianBlur(0.6))
save(court, "T_GymCourt")

# --- gym wall scoreboard (switched off between games: dim amber digits) ---
gs = Image.new("RGB", (2000, 800), (16, 16, 18))
gsd = ImageDraw.Draw(gs)
gsd.rectangle([0, 0, 1999, 120], fill=GREEN)
centred(gsd, (0, 0, 2000, 120), "HOME OF THE HAWKS", font(80), (240, 240, 240))
for x0, label in ((80, "HOME"), (1400, "GUEST")):
    centred(gsd, (x0, 150, x0 + 520, 260), label, font(90), (230, 230, 230))
    gsd.rectangle([x0 + 40, 280, x0 + 480, 640], fill=(30, 12, 8))
    centred(gsd, (x0 + 40, 280, x0 + 480, 640), "00", font(300), (110, 60, 20))
gsd.rectangle([760, 220, 1240, 480], fill=(30, 12, 8))
centred(gsd, (760, 220, 1240, 480), "0:00", font(190), (110, 60, 20))
centred(gsd, (760, 520, 1240, 600), "PERIOD", font(70), (230, 230, 230))
gsd.rectangle([940, 620, 1060, 740], fill=(30, 12, 8))
centred(gsd, (940, 620, 1060, 740), "0", font(100), (110, 60, 20))
save_pot(gs, "T_GymScoreboard", (1024, 512))

# --- window at night (club sparring night): dark street, lit windows, street lights ---
V = 1024
nv = np.zeros((V, V * 2, 3), np.float32)
t = np.linspace(0, 1, V)[:, None]
nv[:] = (np.array([0.02, 0.03, 0.08]) * (1 - t) + np.array([0.10, 0.08, 0.12]) * t)[:, None, :]
night = Image.fromarray((nv * 255).astype(np.uint8))
nd = ImageDraw.Draw(night)
x0 = 0
while x0 < V * 2:
    w = int(vrng.integers(140, 340))
    top = int(vrng.integers(160, 560))
    shade = int(vrng.integers(14, 30))
    nd.rectangle([x0, top, x0 + w, V], fill=(shade, shade, shade + 8))
    for wy in range(top + 30, V - 80, 56):
        for wx in range(x0 + 18, x0 + w - 30, 46):
            if vrng.random() < 0.45:
                warm = vrng.random() < 0.7
                nd.rectangle([wx, wy, wx + 24, wy + 30], fill=(250, 200, 120) if warm else (170, 200, 240))
    x0 += w + int(vrng.integers(0, 30))
for i in range(9):
    cx_ = int(vrng.integers(0, V * 2))
    nd.ellipse([cx_ - 40, 760, cx_ + 40, 840], fill=(255, 210, 140))
nd.rectangle([0, V - 70, V * 2, V], fill=(22, 22, 26))
night = night.filter(ImageFilter.GaussianBlur(8))
save(night, "T_WindowNight")

# --- club dojang: capstone club banner, volunteer team photo, tenets poster (GDD easter egg "Capstone Club") ---
cb = Image.new("RGB", (2400, 800), (246, 246, 244))
cbd = ImageDraw.Draw(cb)
cbd.polygon([(0, 0), (260, 0), (120, 800), (0, 800)], fill=NAVY_D)
cbd.polygon([(300, 0), (380, 0), (240, 800), (160, 800)], fill=RED_HONG)
cbd.polygon([(2400, 0), (2140, 0), (2280, 800), (2400, 800)], fill=NAVY_D)
cbd.polygon([(2100, 0), (2020, 0), (2160, 800), (2240, 800)], fill=BLUE_CHUNG)
km = kicker_mark(520, NAVY_D + (255,))
cb.paste(km, (420, 140), km)
centred(cbd, (900, 120, 2080, 420), "BCIT CAPSTONE CLUB", fit_font(cbd, "BCIT CAPSTONE CLUB", 1150, 200), NAVY_D)
cbd.rectangle([960, 450, 2020, 462], fill=RED_HONG)
centred(cbd, (900, 480, 2080, 600), "OPEN STANCE MOTION CAPTURE TEAM",
        fit_font(cbd, "OPEN STANCE MOTION CAPTURE TEAM", 1100, 80), NAVY_D)
centred(cbd, (900, 600, 2080, 700), "THANK YOU TO OUR VOLUNTEERS", font(60), (90, 90, 100))
save_pot(cb, "T_ClubBanner", (2048, 1024))

# Stand-in team photo: a stylized group in doboks until the real photo of the capture volunteers exists.
ta = np.zeros((1000, 1500, 3), np.float32)
ty = np.linspace(0, 1, 1000)[:, None]
ta[:] = (np.array([0.36, 0.42, 0.52]) * (1 - ty) + np.array([0.70, 0.62, 0.50]) * ty)[:, None, :]
tp = Image.fromarray((ta * 255).astype(np.uint8))
tpd = ImageDraw.Draw(tp)
tpd.rectangle([0, 760, 1500, 1000], fill=(38, 62, 150))      # blue mat
SKIN = [(244, 208, 177), (224, 172, 135), (190, 135, 95), (141, 92, 60), (96, 62, 40)]
HAIR = [(20, 16, 14), (60, 40, 25), (110, 75, 40), (30, 24, 20)]
BELTS = [(15, 15, 15), (15, 15, 15), (200, 30, 40), (30, 70, 170), (40, 130, 60)]
for row_i, (y_base, n, s_) in enumerate(((560, 6, 1.0), (760, 5, 1.12))):
    for k in range(n):
        cx_ = 1500 / 2 + (k - (n - 1) / 2) * 210
        sk = SKIN[int(vrng.integers(0, len(SKIN)))]
        tpd.polygon([(cx_ - 70 * s_, y_base), (cx_ + 70 * s_, y_base), (cx_ + 58 * s_, y_base - 230 * s_),
                     (cx_ - 58 * s_, y_base - 230 * s_)], fill=(240, 240, 236))                     # dobok
        tpd.polygon([(cx_ - 30 * s_, y_base - 230 * s_), (cx_ + 30 * s_, y_base - 230 * s_), (cx_, y_base - 150 * s_)],
                    fill=(20, 20, 20))                                                             # V collar
        tpd.rectangle([cx_ - 64 * s_, y_base - 92 * s_, cx_ + 64 * s_, y_base - 74 * s_],
                      fill=BELTS[int(vrng.integers(0, len(BELTS)))])                              # belt
        tpd.ellipse([cx_ - 40 * s_, y_base - 320 * s_, cx_ + 40 * s_, y_base - 225 * s_], fill=sk)  # head
        tpd.chord([cx_ - 42 * s_, y_base - 326 * s_, cx_ + 42 * s_, y_base - 250 * s_], 180, 360,
                  fill=HAIR[int(vrng.integers(0, len(HAIR)))])
tpd.rectangle([0, 900, 1500, 1000], fill=(246, 246, 244))
centred(tpd, (0, 900, 1500, 1000), "MOTION CAPTURE VOLUNTEERS", font(56), NAVY_D)
tp = tp.filter(ImageFilter.GaussianBlur(1.2))
save_pot(tp, "T_TeamPhoto", (1024, 1024))

tn = Image.new("RGB", (900, 1200), (246, 244, 238))
tnd = ImageDraw.Draw(tn)
tnd.rectangle([0, 0, 900, 220], fill=NAVY_D)
centred(tnd, (0, 20, 900, 200), "TENETS OF TAEKWONDO", fit_font(tnd, "TENETS OF TAEKWONDO", 800, 90), (246, 246, 244))
for i, word in enumerate(("COURTESY", "INTEGRITY", "PERSEVERANCE", "SELF-CONTROL", "INDOMITABLE SPIRIT")):
    yy = 290 + i * 170
    tnd.rectangle([80, yy + 40, 110, yy + 70], fill=RED_HONG if i % 2 == 0 else BLUE_CHUNG)
    tnd.text((150, yy + 18), word, fill=NAVY_D, font=fit_font(tnd, word, 680, 80))
save_pot(tn, "T_ClubTenets", (1024, 1024))

# --- event branding per Career tier: perimeter boards, LED ribbons, screens (event names are fictional) ---
EVENTS = {
    "City": ("CITY OPEN", "TAEKWONDO SPARRING", (18, 64, 48), (240, 200, 60)),
    "Provincial": ("PROVINCIAL CHAMPIONSHIP", "TAEKWONDO KYORUGI", NAVY_D, (240, 240, 240)),
    "National": ("NATIONAL CHAMPIONSHIP", "TAEKWONDO KYORUGI", (10, 12, 20), (240, 240, 240)),
    "Continental": ("CONTINENTAL OPEN", "TAEKWONDO KYORUGI", (8, 30, 72), (230, 200, 120)),
    "World": ("WORLD SERIES FINAL", "TAEKWONDO KYORUGI", (6, 6, 8), GOLD),
}


def event_strip(w, h, title, sub, bg, accent):
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    slant = h * 0.3
    for i, col in enumerate((BLUE_CHUNG, RED_HONG)):
        x = w - h * (0.75 - 0.3 * i)
        d.polygon([(x, h), (x + slant * 0.5, h), (x + slant * 1.5, 0), (x + slant, 0)], fill=col)
    left = int(h * 0.12)
    km_ = kicker_mark(int(h * 0.72), accent + (255,))
    im.paste(km_, (left, (h - km_.height) // 2), km_)
    left += km_.width + int(h * 0.15)
    right = int(w - h * 0.85)
    # title and subtitle as one block, centred vertically
    ft = fit_font(d, title, right - left, int(h * 0.42))
    fs = fit_font(d, sub, right - left, int(h * 0.17))
    bb, bb2 = d.textbbox((0, 0), title, font=ft), d.textbbox((0, 0), sub, font=fs)
    th, sh, gap = bb[3] - bb[1], bb2[3] - bb2[1], h * 0.08
    top = (h - th - gap - sh) / 2
    d.text((left - bb[0], top - bb[1]), title, fill=(245, 245, 245), font=ft)
    d.text((left - bb2[0], top + th + gap - bb2[1]), sub, fill=accent, font=fs)
    return im


for tier, (title, sub, bg, accent) in EVENTS.items():
    save_pot(event_strip(1600, 400, title, sub, bg, accent), f"T_Ad_{tier}", (2048, 512))
    save_pot(event_strip(1500, 500, title, sub, bg, accent), f"T_Banner_{tier}", (2048, 1024))
    rib = Image.new("RGB", (4000, 500), bg)
    for k in range(2):
        rib.paste(event_strip(2000, 500, title, sub, bg, accent), (k * 2000, 0))
    save_pot(rib, f"T_Ribbon_{tier}", (4096, 512))
    # big screen between bouts: event title over the Chung and Hong colours
    sc = Image.new("RGB", (2000, 1000), bg)
    scd = ImageDraw.Draw(sc)
    scd.polygon([(0, 1000), (0, 640), (900, 1000)], fill=BLUE_CHUNG)
    scd.polygon([(2000, 1000), (2000, 640), (1100, 1000)], fill=RED_HONG)
    km_ = kicker_mark(380, accent + (255,))
    sc.paste(km_, ((2000 - km_.width) // 2, 90), km_)
    centred(scd, (100, 520, 1900, 700), title, fit_font(scd, title, 1700, 150), (245, 245, 245))
    centred(scd, (100, 720, 1900, 820), sub, font(64), accent)
    save_pot(sc, f"T_Screen_{tier}", (2048, 1024))

# --- court number signs for the multi-mat provincial hall ---
for n_ in (1, 2, 3):
    cs = Image.new("RGB", (512, 512), NAVY_D)
    csd = ImageDraw.Draw(cs)
    csd.rectangle([0, 0, 512, 110], fill=RED_HONG if n_ % 2 else BLUE_CHUNG)
    centred(csd, (0, 0, 512, 110), "COURT", font(80), (245, 245, 245))
    centred(csd, (0, 120, 512, 500), str(n_), font(330), (245, 245, 245))
    save(cs, f"T_CourtNumber_{n_}")


# --- national flags for the continental arena (simple geometric flags only, official proportions) ---
def flag_stripes(colours, vertical, ratio=(3, 2), weights=None):
    W_, H_ = 900, int(900 * ratio[1] / ratio[0])
    im = Image.new("RGB", (W_, H_))
    d = ImageDraw.Draw(im)
    weights = weights or [1] * len(colours)
    total, pos = sum(weights), 0
    for c, wgt in zip(colours, weights):
        if vertical:
            d.rectangle([W_ * pos / total, 0, W_ * (pos + wgt) / total, H_], fill=c)
        else:
            d.rectangle([0, H_ * pos / total, W_, H_ * (pos + wgt) / total], fill=c)
        pos += wgt
    return im


def nordic(bg, cross, ratio_w, ratio_h, cross_w, cx_units, inner=None, inner_w=0):
    """Nordic cross; all sizes in the flag's own units (ratio_w x ratio_h)."""
    W_, H_ = 900, int(900 * ratio_h / ratio_w)
    u = W_ / ratio_w
    im = Image.new("RGB", (W_, H_), bg)
    d = ImageDraw.Draw(im)
    cx_ = cx_units * u
    for cw, col in ((cross_w, cross), (inner_w, inner)):
        if col:
            d.rectangle([cx_ - cw * u / 2, 0, cx_ + cw * u / 2, H_], fill=col)
            d.rectangle([0, H_ / 2 - cw * u / 2, W_, H_ / 2 + cw * u / 2], fill=col)
    return im


FLAGS = {
    "FRA": flag_stripes([(0, 38, 84), (255, 255, 255), (206, 17, 38)], True),
    "ITA": flag_stripes([(0, 146, 70), (255, 255, 255), (206, 43, 55)], True),
    "IRL": flag_stripes([(22, 155, 98), (255, 255, 255), (255, 136, 62)], True, (2, 1)),
    "BEL": flag_stripes([(0, 0, 0), (253, 218, 36), (239, 51, 64)], True, (15, 13)),
    "NGA": flag_stripes([(0, 135, 81), (255, 255, 255), (0, 135, 81)], True, (2, 1)),
    "DEU": flag_stripes([(0, 0, 0), (221, 0, 0), (255, 206, 0)], False, (5, 3)),
    "NLD": flag_stripes([(174, 28, 40), (255, 255, 255), (33, 70, 139)], False),
    "AUT": flag_stripes([(200, 16, 46), (255, 255, 255), (200, 16, 46)], False),
    "POL": flag_stripes([(255, 255, 255), (220, 20, 60)], False, (8, 5)),
    "COL": flag_stripes([(252, 209, 22), (0, 56, 147), (206, 17, 38)], False, (3, 2), [2, 1, 1]),
    "THA": flag_stripes([(165, 25, 49), (244, 245, 248), (45, 42, 74), (244, 245, 248), (165, 25, 49)], False,
                        (3, 2), [1, 1, 2, 1, 1]),
    "SWE": nordic((0, 106, 167), (254, 204, 0), 16, 10, 2, 6),
    "DNK": nordic((200, 16, 46), (255, 255, 255), 37, 28, 4, 14),
    "FIN": nordic((255, 255, 255), (0, 47, 108), 18, 11, 3, 6.5),
    "NOR": nordic((186, 12, 47), (255, 255, 255), 22, 16, 4, 8, (0, 32, 91), 2),
}
jp = Image.new("RGB", (900, 600), (255, 255, 255))
ImageDraw.Draw(jp).ellipse([450 - 180, 300 - 180, 450 + 180, 300 + 180], fill=(188, 0, 45))   # disc = 3/5 height
FLAGS["JPN"] = jp
FLAGS["KOR"] = Image.open(os.path.join(OUT, "T_Taegukgi.png"))
for code, im in FLAGS.items():
    save_pot(im.convert("RGB"), f"T_Flag_{code}", (512, 512))

# --- world-final entrance screen and podium numbers ---
ey, ex = np.mgrid[0:1000, 0:2000].astype(np.float32)
ang_ = np.arctan2(ey - 1100, ex - 1000)
rays = (0.5 + 0.5 * np.cos(ang_ * 28)) ** 6 * np.clip(1 - np.hypot(ex - 1000, ey - 1100) / 1500, 0, 1)
ea = np.zeros((1000, 2000, 3), np.float32)
ea[..., 0] = rays * np.where(ex < 1000, 0.15, 0.85)
ea[..., 1] = rays * 0.15
ea[..., 2] = rays * np.where(ex < 1000, 0.9, 0.2)
es = Image.fromarray((np.clip(ea + np.array([0.015, 0.015, 0.03]), 0, 1) * 255).astype(np.uint8))
esd = ImageDraw.Draw(es)
km_ = kicker_mark(360, GOLD + (255,))
es.paste(km_, ((2000 - km_.width) // 2, 120), km_)
centred(esd, (100, 520, 1900, 720), "WORLD SERIES FINAL", fit_font(esd, "WORLD SERIES FINAL", 1700, 180), (250, 246, 236))
centred(esd, (100, 740, 1900, 830), "CHUNG  ·  HONG", font(70), GOLD)
save_pot(es, "T_EntranceScreen", (2048, 1024))

for n_, col in ((1, GOLD), (2, (190, 194, 200)), (3, (176, 112, 64))):
    pn = Image.new("RGB", (512, 512), (246, 246, 244))
    pnd = ImageDraw.Draw(pn)
    pnd.rectangle([0, 440, 512, 512], fill=col)
    centred(pnd, (0, 20, 512, 430), str(n_), font(380), NAVY_D)
    save(pn, f"T_Podium{n_}")
