#!/usr/bin/env bash
# Export every premade fighter's portrait (Tools/Blender/portrait_roster.json): the built body of its type and sex
# (FinalRefinement/Portrait/<Kind>_<Sex>/Candidate.blend, from build_portrait_fighters.sh) with the fighter's skin tone,
# hair, eyebrows and head set. Output Resources/Models/FinalRefinement/Portrait/Roster/<Key>/SK_Portrait_<Key>.fbx, logs
# Saved/Logs/roster_<Key>.log; three at a time.
#     bash Tools/Blender/build_roster_portraits.sh [Key ...]
set -u
ROOT=D:/Open-Stance-Gyeorugi
BLENDER="$ROOT/Saved/Tools/Blender522/blender.exe"
SRC=$ROOT/Resources/Models/FinalRefinement/Portrait
ROSTER=$ROOT/Tools/Blender/portrait_roster.json
# one line per fighter: key kind sex look-args (read with Blender's Python, no system Python needed)
LINES=$(MSYS_NO_PATHCONV=1 "$BLENDER" -b --factory-startup --python-expr "
import json
for f in json.load(open(r'$ROSTER'))['fighters']:
    print('ROSTER', f['key'], f['kind'], f['sex'], ' '.join(f'{k}={f[k]}' for k in ('SkinTone', 'HairStyle', 'HairColor', 'EyeColor', 'EyebrowStyle', 'HeadStyle')))
" 2>/dev/null | grep '^ROSTER ' | cut -d' ' -f2-)
WANT=" ${*:-} "
JOBS=3
running=0
while read -r key kind sex look; do
    [ -z "$key" ] && continue
    [ "$WANT" != "  " ] && [[ "$WANT" != *" $key "* ]] && continue
    (
        dir=$SRC/Roster/$key; mkdir -p "$dir"
        MSYS_NO_PATHCONV=1 "$BLENDER" -b "$SRC/${kind}_${sex}/Candidate.blend" --python-exit-code 1 \
            -P "$ROOT/Tools/Blender/export_portrait_fighter.py" -- "$dir/SK_Portrait_$key.fbx" $look \
            > "$ROOT/Saved/Logs/roster_$key.log" 2>&1 && echo "ROSTER DONE $key" || echo "ROSTER FAILED $key"
    ) &
    running=$((running + 1))
    if [ "$running" -ge "$JOBS" ]; then wait -n; running=$((running - 1)); fi
done <<< "$LINES"
wait
echo "ALL ROSTER PORTRAITS FINISHED"
