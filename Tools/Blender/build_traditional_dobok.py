"""Dress a fighter in the traditional wrap-front dobok, one layer at a time, each fitted over the layers under it.

    blender.exe -b <fighter.blend> -P build_traditional_dobok.py -- <out folder>

Layers, in dressing order (each script drapes or fits against everything already on, and skins from the layer beneath):
  1. body                           (the fighter's own Body; nothing to build)
  2. trousers                       build_traditional_trousers.py
  3. jacket top: torso and sleeves  build_traditional_jacket_top.py
  4. jacket skirt                   build_traditional_jacket_skirt.py (carries the jacket body on down over the trousers)
  5. collar band                    build_traditional_collar.py
  6. belt                           fit_belt_over_dobok.py (cinched over the finished jacket)
  7. chest protector and headgear   fit_protector_over_dobok.py (switches them on; hangs over the belt; jacket pressed under)
  8. protector hem retract          fit_protector_hip_lift.py (hip-driven keys: a raised thigh pushes the hem up)
  9. hidden inner layers            hide_covered_layers.py (masks what an outer layer always covers, so it cannot show)
 10. belt tail chains               add_belt_chain_layer.py (bones for engine physics: the knee pushes the tails)
Start from the fighter's original file every time: changing a layer means rebuilding every layer above it.
Saves <out folder>/Candidate.blend and each layer's report.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAYERS = ('build_traditional_trousers.py', 'build_traditional_jacket_top.py', 'build_traditional_jacket_skirt.py',
          'build_traditional_collar.py', 'fit_belt_over_dobok.py', 'fit_protector_over_dobok.py',
          'fit_protector_hip_lift.py', 'hide_covered_layers.py',
          'add_belt_chain_layer.py')
UPTO = int(next((a.split('=')[1] for a in sys.argv if a.startswith('--upto=')), len(LAYERS)))  # debug: stop after N layers
for name in LAYERS[:UPTO]:
    print('LAYER', name, flush=True)
    path = HERE / name
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), {'__name__': '__main__', '__file__': str(path)})
print('DOBOK DONE', flush=True)
