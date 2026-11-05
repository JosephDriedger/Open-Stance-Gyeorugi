"""Contact sheets from Tools/Unreal/capture_match_poses.py: rows are poses, columns the four views, ROWS poses a page.

    python Tools/Validation/match_pose_sheet.py [Fighter ...]   -> Saved/Screenshots/MatchPoses/<Fighter>_sheet<N>.png
"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = "D:/Open-Stance-Gyeorugi/Saved/Screenshots/MatchPoses"
VIEWS = ["front", "left", "back", "right"]
TILE, ROWS = (300, 400), 4

names = sys.argv[1:] or sorted(d for d in os.listdir(ROOT) if os.path.isdir(f"{ROOT}/{d}"))
for name in names:
    for old in os.listdir(ROOT):
        if old.startswith(f"{name}_sheet"):
            os.remove(f"{ROOT}/{old}")
    files = os.listdir(f"{ROOT}/{name}")
    poses = sorted({f.rsplit("_", 1)[0] for f in files}, key=lambda p: (p != "Stance_50", p))
    for page in range(0, len(poses), ROWS):
        chunk = poses[page:page + ROWS]
        sheet = Image.new("RGB", (TILE[0] * 4, TILE[1] * len(chunk)), "black")
        draw = ImageDraw.Draw(sheet)
        for r, pose in enumerate(chunk):
            for c, view in enumerate(VIEWS):
                path = f"{ROOT}/{name}/{pose}_{view}.png"
                if os.path.exists(path):
                    sheet.paste(Image.open(path).convert("RGB").resize(TILE), (c * TILE[0], r * TILE[1]))
            draw.text((6, r * TILE[1] + 6), pose, fill="yellow")
        sheet.save(f"{ROOT}/{name}_sheet{page // ROWS + 1}.png")
    print(name, len(poses))
