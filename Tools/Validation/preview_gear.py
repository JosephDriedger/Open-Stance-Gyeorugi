"""Quick software preview of fitted gear (no Blender or Unreal): shaded views from the exported FBX files.

    py Tools/Validation/preview_gear.py --fitted Saved/CleanTest/Fitted/MH_FighterBase_Body --out Saved/Previews/base
        [--body MH_FighterBase] [--gear] [--dobok]

Writes front, three-quarter, side and back views plus head/chest and hands close-ups. Colours come from the
role patches of the make_gear_textures.py atlas (cloth, belt, collar, trim, team, vinyl); skin is a flat
tone. Orthographic, Lambert-lit, painter's-algorithm sorted: good for judging shape, seams and layering, not
materials (use Tools/Unreal/capture_fighters.py for those).
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_gear_poses as c  # noqa: E402

ROLE_COLOUR = {0: (236, 236, 240), 1: (28, 28, 32), 2: (70, 70, 76), 3: (28, 28, 32), 4: (30, 78, 210), 5: (232, 232, 238)}
SKIN = (196, 150, 126)
DOBOK_ONLY = ("Jacket", "Pants", "Belt")
ALL_PARTS = ("Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards")


def role_of(uv):
    u, v = uv[0] % 1.0, uv[1] % 1.0
    return ROLE_COLOUR.get(int((1 - v) * 4) * 4 + int(u * 4), (200, 0, 200))


def triangles(mesh, verts, colour=None):
    """(n, 3, 3) positions and (n, 3) colours for a mesh, fan-triangulated."""
    tris, cols = [], []
    li = 0
    for f in mesh["faces"]:
        k = len(f)
        col = colour or (role_of(mesh["uv"][li]) if mesh["uv"] is not None else (200, 0, 200))
        li += k
        for i in range(1, k - 1):
            tris.append(verts[[f[0], f[i], f[i + 1]]])
            cols.append(col)
    return np.array(tris), np.array(cols, float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fitted", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--body", default="MH_FighterBase")
    ap.add_argument("--dobok", action="store_true", help="jacket, pants and belt only")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    keep = DOBOK_ONLY if a.dobok else ALL_PARTS

    body = c.load_fbx(os.path.join(c.MODELS, "MetaHuman", f"{a.body}_Body.fbx"))
    head = c.load_fbx(os.path.join(c.MODELS, "MetaHuman", f"{a.body}_Head.fbx"))
    pose = c.Pose(body["G"], body["parent"])
    T, C = [], []
    bm = max(body["meshes"].values(), key=lambda m: len(m["v"]))
    hm = max(head["meshes"].values(), key=lambda m: len(m["v"]))
    for m, par, g in ((bm, body["parent"], body), (hm, head["parent"], head)):
        t, col = triangles(m, c.skin(m, pose, par), SKIN)
        T.append(t)
        C.append(col)
    for p in keep:
        g = c.load_fbx(os.path.join(a.fitted, f"SK_Fighter_{p}.fbx"))
        m = max(g["meshes"].values(), key=lambda m: len(m["v"]))
        t, col = triangles(m, c.skin(m, pose, g["parent"]))
        T.append(t)
        C.append(col)
    T, C = np.concatenate(T), np.concatenate(C)
    G = body["G"]

    def render(name, yaw, centre, scale, size=900):
        r = math.radians(yaw)
        rot = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
        P = (T - centre) @ rot.T
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ln[ln == 0] = 1
        n = n / ln[:, None]
        facing = n[:, 1] < 0                                  # camera at -y looking +y
        light = np.array([-0.35, -0.8, 0.5])
        light /= np.linalg.norm(light)
        shade = 0.40 + 0.60 * np.abs(n @ light)
        depth = P[:, :, 1].mean(1)
        order = np.argsort(-depth)
        img = Image.new("RGB", (size, size), (58, 60, 66))
        dr = ImageDraw.Draw(img)
        x = size / 2 + P[:, :, 0] * scale
        y = size / 2 - P[:, :, 2] * scale
        for i in order:
            col = tuple(int(min(255, v * shade[i])) for v in C[i])
            dr.polygon([(x[i, 0], y[i, 0]), (x[i, 1], y[i, 1]), (x[i, 2], y[i, 2])], fill=col)
        img.save(os.path.join(a.out, name + ".png"))

    # positions are in centimetres
    for name, yaw in (("front", 0), ("three_quarter", 35), ("side", 90), ("back", 180)):
        render(name, yaw, np.array([0.0, 0.0, 95.0]), 4.5)
    head_z = G["head"][:3, 3][2]
    render("head_chest", 20, np.array([0.0, 0.0, head_z - 12.0]), 24.0)
    hl = G["hand_l"][:3, 3]
    render("hand", 30, hl.copy(), 32.0)
    fl = G["foot_l"][:3, 3]
    render("foot", 30, np.array([fl[0], fl[1], fl[2] + 3.0]), 32.0)
    render("crotch", 0, np.array([0.0, 0.0, G["pelvis"][:3, 3][2] - 5.0]), 17.0)
    print("previews in", a.out)


if __name__ == "__main__":
    main()
