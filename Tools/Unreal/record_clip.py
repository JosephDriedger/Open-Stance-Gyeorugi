"""Record a silent video clip of the running game, HUD included, with no window on screen.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject /Game/Maps/L_TrainingDojang -game -RenderOffscreen
        -unattended -SCCProvider=None -nosound -benchmark -fps=30 -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/record_clip.py <clip>"

-benchmark -fps=30 steps the game exactly 1/30 s per frame however slow the offscreen render is, so the clip plays at real
speed. Every frame is saved with `shot showui` (Unreal's -dumpmovie leaves out Slate, so it would miss the HUD, captions and
debug bars). Frames: Saved/Clips/<clip>/f00000.png..., then Tools/encode_clips.py makes the MP4. Log: Saved/Logs/record_clip.txt.
"""
import os
import sys
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
ROWS = ["SideKick_Trunk", "Roundhouse_Trunk", "Hook_Head", "Axe_Head", "Punch_Trunk", "SpinSide_Trunk", "SpinHook_Head",
        "Tornado_Trunk"]
WARMUP = 45          # frames before recording starts (fighters and HUD settle)


def techniques(camera):
    """Each technique thrown in turn, 75 frames (2.5 s) apart."""
    events = [(0, f"os.CameraPreset {camera}"), (0, "os.ShowHitboxes 1"), (0, "os.InfiniteStamina 1")]
    if camera == "Match":
        events.append((0, "os.CombatDebug 1"))
    for i, row in enumerate(ROWS):
        events.append((20 + i * 75, f"os.Throw {row}"))
    return events, 20 + len(ROWS) * 75 + 30


# clip name: (console commands by frame after the warm-up, frames to record)
CLIPS = {
    # The proof is about 10 s of action; half speed leaves time to talk over each stage.
    "01_greybox_proof": ([(0, "slomo 0.5"), (0, "os.PlayProof")], 900),
    "02_proof_side_hitboxes": ([(0, "slomo 0.5"), (0, "os.CameraPreset SideBroadcast"), (0, "os.ShowHitboxes 1"),
                                (0, "os.PlayProof")], 780),
    "03_techniques_side": techniques("SideBroadcast"),
    "04_techniques_behind": techniques("Match"),
    "05_menu_flow": ([(0, "OpenStance.Menu.Show Title"), (75, "OpenStance.Menu.Show Main"),
                      (165, "OpenStance.Menu.Show Sparring"), (255, "OpenStance.Menu.Show SideSelect"),
                      (345, "OpenStance.Menu.Show FighterSelect"), (450, "OpenStance.Menu.Show Controls")], 540),
    "06_arena_cameras": ([(0, "os.CameraPreset SideHigh"), (10, "os.Throw Roundhouse_Trunk"),
                          (90, "os.CameraPreset ThreeQuarterCorner"), (100, "os.Throw SideKick_Trunk"),
                          (180, "os.CameraPreset BehindLow"), (190, "os.Throw Axe_Head"),
                          (270, "os.CameraPreset HighJudge"), (280, "os.Throw SpinHook_Head")], 360),
}


class Recorder:
    def __init__(self, clip):
        self.clip = clip
        self.events, self.frames = CLIPS[clip]
        self.out = f"{REPO}/Saved/Clips/{clip}"
        os.makedirs(self.out, exist_ok=True)
        for name in os.listdir(self.out):
            if name.endswith(".png"):
                os.remove(os.path.join(self.out, name))
        self.f = open(f"{REPO}/Saved/Logs/record_clip.txt", "a", encoding="utf-8")
        self.tick_count = 0
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        self.log(f"recording {clip}: {self.frames} frames")

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()

    def context(self):
        for pc in unreal.ObjectIterator(unreal.PlayerController):
            if pc.get_world() is not None:
                return pc
        return None

    def run(self, cmd):
        unreal.SystemLibrary.execute_console_command(self.context(), cmd)

    def tick(self, dt):
        try:
            self.tick_count += 1
            frame = self.tick_count - WARMUP
            if frame < 0:
                return
            for at, cmd in self.events:
                if at == frame:
                    self.log(f"{frame}: {cmd}")
                    self.run(cmd)
            if frame < self.frames:
                self.run(f"shot showui filename={self.out}/f{frame:05d}.png nosuffix")
            elif frame == self.frames + 5:      # the last shots are written a frame or two later
                self.log("done")
                unreal.unregister_slate_post_tick_callback(self.handle)
                self.run("quit")
        except Exception:
            self.log("ERROR\n" + traceback.format_exc())
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.run("quit")


Recorder(sys.argv[1] if len(sys.argv) > 1 else "01_greybox_proof")
