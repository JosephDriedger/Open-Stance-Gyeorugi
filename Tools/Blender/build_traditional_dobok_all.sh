#!/usr/bin/env bash
# Build the layered traditional dobok for every body type: start file (Gameplay_High + the kick test), the ten layers,
# and the Unreal test FBX. Runs JOBS bodies at a time; logs to Saved/Logs/dobok_<Kind>.log.
#     bash Tools/Blender/build_traditional_dobok_all.sh [Kind ...]
set -u
ROOT=D:/Open-Stance-Gyeorugi
BLENDER="$ROOT/Saved/Tools/Blender522/blender.exe"
OUT=$ROOT/Resources/Models/FinalRefinement/TraditionalDobok
KINDS=${*:-Compact Tall LeanTall Female_Athletic Female_Strong Male_Athletic Male_Lean}
JOBS=2
build() {
    local kind=$1 log=$ROOT/Saved/Logs/dobok_$1.log
    {
        MSYS_NO_PATHCONV=1 "$BLENDER" -b "$ROOT/Resources/Models/CharacterSuite/$kind/Gameplay_High.blend" --python-exit-code 1 \
            -P "$ROOT/Tools/Blender/prepare_dobok_start.py" -- "$OUT/$kind/Work.blend" &&
        MSYS_NO_PATHCONV=1 "$BLENDER" -b "$OUT/$kind/Work.blend" --python-exit-code 1 \
            -P "$ROOT/Tools/Blender/build_traditional_dobok.py" -- "$OUT/$kind" &&
        MSYS_NO_PATHCONV=1 "$BLENDER" -b "$OUT/$kind/Candidate.blend" --python-exit-code 1 \
            -P "$ROOT/Tools/Blender/export_skirt_cloth_test.py" -- "$OUT/$kind/${kind}_TraditionalDobok.fbx" &&
        echo "BODY DONE $kind" || echo "BODY FAILED $kind"
    } > "$log" 2>&1
    grep -hE "BODY (DONE|FAILED)" "$log"
}
running=0
for kind in $KINDS; do
    build "$kind" &
    running=$((running + 1))
    if [ "$running" -ge "$JOBS" ]; then wait -n; running=$((running - 1)); fi
done
wait
echo "ALL BODIES FINISHED"
