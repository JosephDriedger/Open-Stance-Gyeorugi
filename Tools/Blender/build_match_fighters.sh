#!/usr/bin/env bash
# Build the match fighters: every premade fighter (Tools/Blender/portrait_roster.json) in the full layered dobok with
# its sparring gear, once per side (Chung blue, Hong red), on the rig the placeholder technique clips are authored on.
#   1. per body type and sex: the portrait start file (prepare_portrait_fighter.py's warp and hair) with gloves and foot
#      guards on, then build_traditional_dobok.py --upto=8 (protector fit, hip lift and hidden covered layers; no belt
#      chain, whose bones are not on the production skeleton), then refine_match_weights.py (smooths the weights wherever
#      the technique clips stretch the dobok) -> FinalRefinement/Match/<Kind>_<Sex>/Candidate.blend
#   2. per fighter and side: export_portrait_fighter.py --gear MatchSide=0|1 with the fighter's look
#      -> FinalRefinement/Match/Roster/<Key>_<Chung|Hong>/SK_Match_<Key>_<Chung|Hong>.fbx
# Needs build_portrait_fighters.sh run first. Logs: Saved/Logs/match_<name>.log.
#     bash Tools/Blender/build_match_fighters.sh [bodies|fighters]   (default: both)
set -u
ROOT=D:/Open-Stance-Gyeorugi
BLENDER="$ROOT/Saved/Tools/Blender522/blender.exe"
PORTRAIT=$ROOT/Resources/Models/FinalRefinement/Portrait
OUT=$ROOT/Resources/Models/FinalRefinement/Match
STEP=${1:-both}
if [ "$STEP" != fighters ]; then
    running=0
    for target in Compact_Male Compact_Female LeanTall_Male LeanTall_Female Stocky_Male Stocky_Female Tall_Male Tall_Female; do
        (
            dir=$OUT/$target; mkdir -p "$dir"; log=$ROOT/Saved/Logs/match_$target.log
            {
                MSYS_NO_PATHCONV=1 "$BLENDER" -b "$PORTRAIT/$target/Work.blend" --python-exit-code 1 --python-expr "
import bpy
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
rig['Wear_Gloves'] = rig['Wear_FootGuards'] = True
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=r'$dir/Work.blend', compress=True)
" &&
                MSYS_NO_PATHCONV=1 "$BLENDER" -b "$dir/Work.blend" --python-exit-code 1 \
                    -P "$ROOT/Tools/Blender/build_traditional_dobok.py" -- "$dir" --upto=8 &&
                MSYS_NO_PATHCONV=1 "$BLENDER" -b "$dir/Candidate.blend" --python-exit-code 1 \
                    -P "$ROOT/Tools/Blender/refine_match_weights.py" -- --save &&
                echo "MATCH BODY DONE $target" || echo "MATCH BODY FAILED $target"
            } > "$log" 2>&1
            grep -hE "MATCH BODY (DONE|FAILED)" "$log"
        ) &
        running=$((running + 1))
        if [ "$running" -ge 2 ]; then wait -n; running=$((running - 1)); fi
    done
    wait
fi
if [ "$STEP" != bodies ]; then
    LINES=$(MSYS_NO_PATHCONV=1 "$BLENDER" -b --factory-startup --python-expr "
import json
for f in json.load(open(r'$ROOT/Tools/Blender/portrait_roster.json'))['fighters']:
    print('ROSTER', f['key'], f['kind'], f['sex'], ' '.join(f'{k}={f[k]}' for k in ('SkinTone', 'HairStyle', 'HairColor', 'EyeColor', 'EyebrowStyle', 'HeadStyle')))
" 2>/dev/null | grep '^ROSTER ' | cut -d' ' -f2-)
    running=0
    while read -r key kind sex look; do
        [ -z "$key" ] && continue
        for side in 0 1; do
            name=${key}_$([ $side = 0 ] && echo Chung || echo Hong)
            (
                dir=$OUT/Roster/$name; mkdir -p "$dir"
                MSYS_NO_PATHCONV=1 "$BLENDER" -b "$OUT/${kind}_${sex}/Candidate.blend" --python-exit-code 1 \
                    -P "$ROOT/Tools/Blender/export_portrait_fighter.py" -- "$dir/SK_Match_$name.fbx" --gear MatchSide=$side $look \
                    > "$ROOT/Saved/Logs/match_$name.log" 2>&1 && echo "MATCH DONE $name" || echo "MATCH FAILED $name"
            ) &
            running=$((running + 1))
            if [ "$running" -ge 3 ]; then wait -n; running=$((running - 1)); fi
        done
    done <<< "$LINES"
    wait
fi
echo "ALL MATCH FIGHTERS FINISHED"
