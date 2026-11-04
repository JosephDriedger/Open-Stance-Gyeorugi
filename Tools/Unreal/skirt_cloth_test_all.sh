#!/usr/bin/env bash
# Run the Unreal cloth + belt-chain test (skirt_cloth_test.py) on every body's traditional-dobok FBX, one editor at a
# time (headless). Captures go to Saved/Screenshots/SkirtCloth/dobok_<Kind>/, the per-run log is copied next to them.
#     bash Tools/Unreal/skirt_cloth_test_all.sh [Kind ...]
set -u
ROOT=D:/Open-Stance-Gyeorugi
EDITOR=/c/UE_5.8.0/Engine/Binaries/Win64/UnrealEditor-Cmd.exe
OUT=$ROOT/Resources/Models/FinalRefinement/TraditionalDobok
KINDS=${*:-Stocky Medium Compact Tall LeanTall Female_Athletic Female_Strong Male_Athletic Male_Lean}
for kind in $KINDS; do
    fbx=$OUT/$kind/${kind}_TraditionalDobok.fbx
    [ -f "$fbx" ] || { echo "UNREAL SKIPPED $kind (no FBX)"; continue; }
    MSYS_NO_PATHCONV=1 "$EDITOR" "$ROOT/OpenStance.uproject" -RenderOffscreen -unattended -SCCProvider=None \
        -ExecCmds="py $ROOT/Tools/Unreal/skirt_cloth_test.py fbx=$fbx kind=$kind max=2 chain tag=dobok_$kind quit" \
        > "$ROOT/Saved/Logs/unreal_dobok_$kind.log" 2>&1
    cp "$ROOT/Saved/Logs/skirt_cloth_test.txt" "$ROOT/Saved/Screenshots/SkirtCloth/dobok_$kind/test_log.txt" 2>/dev/null
    if grep -q "^DONE" "$ROOT/Saved/Logs/skirt_cloth_test.txt" && ! grep -q "^ERROR" "$ROOT/Saved/Logs/skirt_cloth_test.txt"; then
        echo "UNREAL DONE $kind"
    else
        echo "UNREAL FAILED $kind"
    fi
done
echo "ALL UNREAL FINISHED"
