#!/usr/bin/env bash
# Build the menu portrait fighters: every body type as a man and a woman, in the traditional dobok without sparring
# gear (prepare_portrait_fighter.py -> build_traditional_dobok.py --upto=5 -> export_portrait_fighter.py). Starts from
# each body's TraditionalDobok/<Kind>/Work.blend (build_traditional_dobok_all.sh makes it). Two builds at a time; logs
# to Saved/Logs/portrait_<Kind>_<Sex>.log, output in Resources/Models/FinalRefinement/Portrait/<Kind>_<Sex>/.
#     bash Tools/Blender/build_portrait_fighters.sh [Kind_Sex ...]
set -u
ROOT=D:/Open-Stance-Gyeorugi
BLENDER="$ROOT/Saved/Tools/Blender522/blender.exe"
SRC=$ROOT/Resources/Models/FinalRefinement/TraditionalDobok
OUT=$ROOT/Resources/Models/FinalRefinement/Portrait
TARGETS=${*:-Compact_Male Compact_Female LeanTall_Male LeanTall_Female Stocky_Male Stocky_Female Tall_Male Tall_Female}
JOBS=2
build() {
    local target=$1 kind=${1%_*} sex=${1##*_} log=$ROOT/Saved/Logs/portrait_$1.log dir=$OUT/$1
    mkdir -p "$dir"
    {
        MSYS_NO_PATHCONV=1 "$BLENDER" -b "$SRC/$kind/Work.blend" --python-exit-code 1 \
            -P "$ROOT/Tools/Blender/prepare_portrait_fighter.py" -- "$sex" "$dir/Work.blend" &&
        MSYS_NO_PATHCONV=1 "$BLENDER" -b "$dir/Work.blend" --python-exit-code 1 \
            -P "$ROOT/Tools/Blender/build_traditional_dobok.py" -- "$dir" --upto=5 &&
        MSYS_NO_PATHCONV=1 "$BLENDER" -b "$dir/Candidate.blend" --python-exit-code 1 \
            -P "$ROOT/Tools/Blender/export_portrait_fighter.py" -- "$dir/SK_Portrait_${target}.fbx" &&
        echo "PORTRAIT DONE $target" || echo "PORTRAIT FAILED $target"
    } > "$log" 2>&1
    grep -hE "PORTRAIT (DONE|FAILED)" "$log"
}
running=0
for target in $TARGETS; do
    build "$target" &
    running=$((running + 1))
    if [ "$running" -ge "$JOBS" ]; then wait -n; running=$((running - 1)); fi
done
wait
echo "ALL PORTRAITS FINISHED"
