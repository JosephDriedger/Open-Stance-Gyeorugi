"""Renders the menu screens to PNG for comparison with the HTML prototype (Docs/Prototype/shots).

Run headless, no window:
  UnrealEditor-Cmd.exe <project> -RenderOffscreen -unattended -ExecCmds="py .../capture_menu.py [name ...] quit"

With no names it captures every screen; with names (e.g. 02_main 06_match) only those. Images go to
Saved/Screenshots/Menu/ at 1600 x 900 (the prototype's capture size) and the log to Saved/Logs/capture_menu.txt.
The names match the prototype's file names, so each image has a counterpart in Docs/Prototype/shots.
"""
import os
import sys

import unreal

SCREEN = unreal.OpenStanceMenuScreen
WIDTH, HEIGHT = 1600, 900

# (file name, screen, state) in the prototype's order; see OpenStanceMenuCaptureLibrary.h for the state keys
SHOTS = [
    ("01_title", SCREEN.TITLE, ""),
    ("02_main", SCREEN.MAIN, ""),
    ("02b_main_progress", SCREEN.MAIN, "hub=1"),
    ("02c_main_connected", SCREEN.MAIN, "hub=2"),
    ("02d_main_options", SCREEN.MAIN, "hub=3"),
    ("03_sparring", SCREEN.SPARRING, ""),
    ("04_tournament", SCREEN.TOURNAMENT, "mode=tournament"),
    ("05_select", SCREEN.FIGHTER_SELECT, ""),
    ("05b_select_women", SCREEN.FIGHTER_SELECT, "category=women"),
    ("06_match", SCREEN.MATCH, "sample=hud"),
    ("07_pause", SCREEN.MATCH, "sample=hud;dialog=pause"),
    ("08_results", SCREEN.RESULTS, "sample=results"),
    ("09_training", SCREEN.TRAINING, ""),
    ("10_career", SCREEN.CAREER, ""),
    ("11_customize", SCREEN.CUSTOMIZE, ""),
    ("11b_customize_female", SCREEN.CUSTOMIZE, "sex=female"),
    ("12_options", SCREEN.OPTIONS, ""),
    ("12b_options_video", SCREEN.OPTIONS, "options_tab=1"),
    ("12c_options_controls", SCREEN.OPTIONS, "options_tab=2"),
    ("12d_options_accessibility", SCREEN.OPTIONS, "options_tab=3"),
    ("13_bracket", SCREEN.BRACKET, ""),
] + [("14_controls_%d" % tab, SCREEN.CONTROLS, "controls_tab=%d" % tab) for tab in range(7)] + [
    ("21_team", SCREEN.TEAM, ""),
    ("22_challenges", SCREEN.CHALLENGES, ""),
    ("23_refmode", SCREEN.REFEREE_SETUP, ""),
    ("24_refmatch", SCREEN.REFEREE_MATCH, ""),
    ("25_refrating", SCREEN.REFEREE_GRADE, ""),
    ("26_online", SCREEN.ONLINE, ""),
    ("27_replays", SCREEN.REPLAYS, ""),
    ("28_broadcast", SCREEN.BROADCAST, ""),
    ("29_longterm", SCREEN.LONG_TERM, ""),
]

out_dir = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "Menu")
log_path = os.path.join(unreal.Paths.project_saved_dir(), "Logs", "capture_menu.txt")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
args = sys.argv[1:]
quit_after = "quit" in args
wanted = set(a for a in args if a != "quit")

lines = []
failed = 0
for name, screen, state in SHOTS:
    if wanted and name not in wanted:
        continue
    path = os.path.join(out_dir, name + ".png").replace("\\", "/")
    ok = unreal.OpenStanceMenuCaptureLibrary.capture_screen(screen, path, state, WIDTH, HEIGHT)
    failed += 0 if ok else 1
    lines.append("%s %s" % ("ok  " if ok else "FAIL", name))

lines.append("%d captured, %d failed" % (len(lines) - failed, failed))
with open(log_path, "w") as log:
    log.write("\n".join(lines) + "\n")
unreal.log("\n".join(lines))
if quit_after:
    unreal.SystemLibrary.quit_editor()
