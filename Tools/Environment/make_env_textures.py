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
