#!/usr/bin/env bash
# Mocap targets with the belt-tail bone chain, written to Resources/Models/Animation/MotionBuilder_BeltChain/<Preset>[/WhiteVNeck]/
# (the installed Animation/MotionBuilder targets are not touched). Per preset, jacket style (plain = WhiteWrap, or WhiteVNeck) and outfit:
#   0. the source FBX is the one the installed target was characterized from (its validation_*.json "source")
#   1. Blender: export the chain rig + tails from BoneChainBelt/<Preset>/Candidate.blend (Tools/Blender/export_chain_tails.py)
#   2. Blender: merge them into a COPY of that source (merge_chain_tails_into_target.py; asserts the tails coincide)
#   3. MotionBuilder: characterize + control rig + save + reopen (prepare_test_character.py)
# Usage: Tools/MotionBuilder/build_belt_chain_targets.sh [Preset ...]    (default: all nine; finished targets are skipped)
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
OUT=Resources/Models/Animation/MotionBuilder_BeltChain; INSTALLED=Resources/Models/Animation/MotionBuilder
WORK="${TMPDIR:-/tmp}/belt_chain_targets"; mkdir -p "$OUT/_Sources" "$WORK"
MOBU="/c/Program Files/Autodesk/MotionBuilder 2027/bin/x64/mobupy.exe"
PRESETS=("$@"); [ ${#PRESETS[@]} -eq 0 ] && PRESETS=(Medium Compact Stocky LeanTall Tall Male_Athletic Male_Lean Female_Athletic Female_Strong)
for kind in "${PRESETS[@]}"; do
  tails="$WORK/${kind}_tails.fbx"
  if [ ! -s "$tails" ]; then
    blender-launcher --background "$ROOT/Resources/Models/FinalRefinement/BoneChainBelt/$kind/Candidate.blend" --python Tools/Blender/export_chain_tails.py -- "$kind" "$tails" "$WORK/${kind}_tails.log" >/dev/null 2>&1
    grep -q DONE "$WORK/${kind}_tails.log" || { echo "FAIL tails $kind: $(tail -1 "$WORK/${kind}_tails.log")"; continue; }
  fi
  for style in "" WhiteVNeck; do
    sub="$kind${style:+/$style}"; mkdir -p "$OUT/$sub"
    for outfit in Dobok Sparring; do
      name="OpenStance_$kind"; [ "$outfit" = Sparring ] && name="OpenStance_${kind}_Sparring"
      tag="$name${style:+_$style}"
      [ -s "$OUT/$sub/validation_$name.json" ] && { echo "SKIP $tag (done)"; continue; }
      ref="$INSTALLED/$sub/validation_$name.json"
      src=$(grep -o '"source": "[^"]*"' "$ref" 2>/dev/null | cut -d'"' -f4)
      [ -s "$src" ] || { echo "FAIL $tag: source '$src' missing (from $ref)"; continue; }
      copy="$WORK/$tag.fbx"; cp "$src" "$copy"
      merged="$OUT/_Sources/${tag}_BeltChain_Source.fbx"
      blender-launcher --background --factory-startup --python Tools/Blender/merge_chain_tails_into_target.py -- "$copy" "$tails" "$ROOT/$merged" "$WORK/${tag}_merge.log" >/dev/null 2>&1
      grep -q "^DONE" "$WORK/${tag}_merge.log" || { echo "FAIL merge $tag: $(grep -m1 -A3 ERROR "$WORK/${tag}_merge.log" | tail -2 | tr '\n' ' ')"; continue; }
      "$MOBU" Tools/MotionBuilder/prepare_test_character.py --source "$merged" --name "$name" --output-dir "$OUT/$sub" >"$WORK/${tag}_mobu.log" 2>&1
      if grep -q '"reopened_successfully": true' "$WORK/${tag}_mobu.log"; then echo "OK   $tag  src=${src#Resources/Models/}  $(grep -o '"wrist_control_hand_movement_cm": [0-9.]*' "$WORK/${tag}_mobu.log" | cut -c36-42)"; else echo "FAIL mobu $tag"; fi
    done
  done
done
