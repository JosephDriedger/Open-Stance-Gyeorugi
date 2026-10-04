"""Generate the clean gear textures used by the carved garments (build_clean_gear.py).

    py Tools/Blender/make_gear_textures.py

Writes to Resources/Models/Textures/:
  T_Fighter_BaseColor.png  sRGB atlas of flat colour patches, one per surface role
  T_Fighter_Masks.png      R team colour, G belt, B collar, A unused (same channel meaning as before)
  T_Fighter_Surface.png    linear: R roughness, G fabric-weave normal strength
  T_Fighter_Weave_N.png    tileable plain-weave normal map (DirectX green), sampled with UV1 (see below)

Each garment face samples one patch by a constant UV0, so colour and masks are exact. Fine surface
detail comes from the weave normal map on UV1, which the garment builder fills with a continuous
projection (tiling in metres), not from the atlas.

Patch luminances match what M_FighterGear's recolour constants were measured against
(Tools/Blender/preview_material.py): team blue 0.0559, belt 0.0036, collar 0.0281.
"""
import os

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "Resources", "Models", "Textures")
SIZE, GRID = 1024, 4

# role: (sRGB base colour, mask RGB, roughness, weave strength)
ROLES = {
    "cloth":  ((238, 237, 239), (0, 0, 0), 0.88, 0.55),   # dobok cotton
    "belt":   ((13, 13, 14),    (0, 255, 0), 0.82, 0.55),
    "collar": ((47, 47, 47),    (0, 0, 255), 0.85, 0.55),
    "trim":   ((13, 13, 14),    (0, 0, 0), 0.70, 0.5),   # piping and cuffs
    "team":   ((17, 55, 168),   (255, 0, 0), 0.55, 0.0), # moulded foam and vinyl, satin, recoloured to Hong in the material
    "vinyl":  ((236, 236, 240), (0, 0, 0), 0.45, 0.0),   # gloves, foot guards
    "binding": ((244, 244, 246), (0, 0, 0), 0.62, 0.35), # white nylon edge binding and straps (WT protector)
    "sensor": ((72, 74, 78),    (0, 0, 0), 0.55, 0.0),   # grey sensor pads and soles (electronic socks)
    "liner":  ((22, 22, 24),    (0, 0, 0), 0.90, 0.0),   # foam inside the helmet and protector edges
}
CELL = {name: (i % GRID, i // GRID) for i, name in enumerate(ROLES)}


def patch_uv(role):
    """UV0 (u, v up) at the centre of a role's patch."""
    c, r = CELL[role]
    return ((c + 0.5) / GRID, 1.0 - (r + 0.5) / GRID)


def weave_normal(n=512, threads=16, strength=2.2):
    """Plain weave: over/under threads with rounded profiles, as a tangent-space normal map."""
    x = (np.arange(n) + 0.5) / n
    u, v = np.meshgrid(x, x)
    ph = 2 * np.pi * threads
    warp = 0.5 + 0.5 * np.cos(ph * u)               # vertical threads (height across u)
    weft = 0.5 + 0.5 * np.cos(ph * v)               # horizontal threads
    over = (np.floor(u * threads) + np.floor(v * threads)) % 2     # checkerboard of who is on top
    h = np.where(over == 0, 0.6 * warp + 0.4 * weft * 0.5, 0.6 * weft + 0.4 * warp * 0.5)
    h += 0.04 * np.random.default_rng(3).standard_normal((n, n))   # fibre noise
    gy, gx = np.gradient(h, 1.0 / n)
    nx, ny, nz = -gx * strength / n * 4, -gy * strength / n * 4, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([nx / ln, -ny / ln, nz / ln], axis=-1) * 0.5 + 0.5    # DirectX: green up is -y
    return (rgb * 255 + 0.5).astype(np.uint8)


def main():
    os.makedirs(OUT, exist_ok=True)
    base = np.zeros((SIZE, SIZE, 3), np.uint8)
    mask = np.zeros((SIZE, SIZE, 4), np.uint8)
    surf = np.zeros((SIZE, SIZE, 3), np.uint8)
    cell = SIZE // GRID
    for name, (col, m, rough, weave) in ROLES.items():
        c, r = CELL[name]
        sl = (slice(r * cell, (r + 1) * cell), slice(c * cell, (c + 1) * cell))
        base[sl] = col
        mask[sl] = (*m, 0)
        surf[sl] = (int(rough * 255 + 0.5), int(weave * 255 + 0.5), 0)
    Image.fromarray(base).save(os.path.join(OUT, "T_Fighter_BaseColor.png"))
    Image.fromarray(mask, "RGBA").save(os.path.join(OUT, "T_Fighter_Masks.png"))
    Image.fromarray(surf).save(os.path.join(OUT, "T_Fighter_Surface.png"))
    Image.fromarray(weave_normal()).save(os.path.join(OUT, "T_Fighter_Weave_N.png"))
    print("textures written to", OUT)
    print({k: tuple(round(x, 4) for x in patch_uv(k)) for k in ROLES})


if __name__ == "__main__":
    main()
