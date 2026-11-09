"""Encode the frames from Tools/Unreal/record_clip.py into silent 30 fps MP4s: Saved/Clips/<clip>.mp4.

    python Tools/encode_clips.py [clip ...]      (no names: every folder in Saved/Clips)
"""
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

CLIPS = Path("D:/Open-Stance-Gyeorugi/Saved/Clips")

names = sys.argv[1:] or sorted(p.name for p in CLIPS.iterdir() if p.is_dir())
for name in names:
    frames = sorted((CLIPS / name).glob("*.png"))
    if not frames:
        print(f"{name}: no frames")
        continue
    size = Image.open(frames[0]).size
    out = CLIPS / f"{name}.mp4"
    writer = imageio_ffmpeg.write_frames(str(out), size, fps=30, codec="libx264", pix_fmt_in="rgb24", pix_fmt_out="yuv420p", macro_block_size=1,
                                         output_params=["-crf", "18", "-preset", "medium"])
    writer.send(None)
    for frame in frames:
        writer.send(Image.open(frame).convert("RGB").tobytes())
    writer.close()
    print(f"{name}: {len(frames)} frames, {len(frames) / 30:.1f} s -> {out}")
