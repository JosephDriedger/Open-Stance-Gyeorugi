"""Assemble the silent Milestone 1 video from Saved/Clips, timed to Docs/M1_Video_Script.docx.

    python Tools/assemble_video.py

Each segment takes part of a clip and fills its slot in the script; a clip shorter than its slot holds its last frame.
Output: Saved/Clips/M1_Video_Silent.mp4 (1920x1080, 30 fps, no audio).
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg

CLIPS = Path("D:/Open-Stance-Gyeorugi/Saved/Clips")
OUT = CLIPS / "M1_Video_Silent.mp4"

# (clip, start in the clip, seconds to take, slot length in the script)
SEGMENTS = [
    ("05_menu_flow", 0.0, 2.4, 15),             # 0:00 title screen, held
    ("01_greybox_proof", 0.0, 30.0, 30),        # 0:15 greybox proof, half speed
    ("03_techniques_side", 0.0, 20.0, 20),      # 0:45 eight techniques
    ("07_code_skill_stick", 0.0, 12.0, 20),     # 1:05 Rider: gesture table
    ("04_techniques_behind", 0.0, 20.0, 20),    # 1:25 debug overlay
    ("08_code_state_machine", 0.0, 12.0, 20),   # 1:45 Rider: state machine
    ("02_proof_side_hitboxes", 0.0, 25.0, 25),  # 2:05 proof side-on with hitboxes
    ("09_code_hit_trace", 0.0, 12.0, 20),       # 2:30 Rider: hit trace
    ("05_menu_flow", 0.0, 18.0, 20),            # 2:50 menus
    ("06_arena_cameras", 0.0, 10.0, 10),        # 3:10 arena and camera presets
    ("01_greybox_proof", 26.0, 4.0, 25),        # 3:20 Results, held (progress)
    ("10_mocap_marker_check", 0.0, 13.0, 15),   # 3:45 mocap: suit and markers
    ("12_mocap_photos", 0.0, 15.0, 15),         # 4:00 mocap photos
    ("11_mocap_capture_volume", 0.0, 15.0, 15), # 4:15 capture volume
    ("13_dojang_reference_kicks", 0.0, 15.0, 15),  # 4:30 dojang reference
    ("06_arena_cameras", 0.0, 12.0, 15),        # 4:45 next milestone, then fade out
]

args = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
for clip, _, _, _ in SEGMENTS:
    args += ["-i", str(CLIPS / f"{clip}.mp4")]

parts = []
for i, (clip, start, take, slot) in enumerate(SEGMENTS):
    hold = max(0.0, slot - take)
    parts.append(f"[{i}:v]trim=start={start}:duration={take},setpts=PTS-STARTPTS,fps=30,scale=1920:1080,setsar=1,"
                 f"tpad=stop_mode=clone:stop_duration={hold},trim=duration={slot},setpts=PTS-STARTPTS[v{i}]")
total = sum(s[3] for s in SEGMENTS)
chain = "".join(f"[v{i}]" for i in range(len(SEGMENTS)))
parts.append(f"{chain}concat=n={len(SEGMENTS)}:v=1:a=0,fade=t=in:st=0:d=0.5,fade=t=out:st={total - 1}:d=1,format=yuv420p[out]")

args += ["-filter_complex", ";".join(parts), "-map", "[out]", "-an", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-r", "30", "-movflags", "+faststart", str(OUT)]
subprocess.run(args, check=True)
print(f"{OUT} ({total // 60}:{total % 60:02d})")
