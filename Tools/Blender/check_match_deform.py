"""Measure how a match fighter's dobok and gear deform through every placeholder technique clip.

    blender.exe -b Resources/Models/FinalRefinement/Match/<Kind>_<Sex>/Candidate.blend -P check_match_deform.py -- <report.json> [step]

Appends the placeholder clips (Resources/Models/Animation/PlaceholderTechniques/PlaceholderTechniques.blend), samples
every `step` frames (default 2) of each (mirrors included) and reports, per shown mesh:

- growth_cm: the most any edge grows; stretch: the largest edge length ratio (edges over MIN_EDGE_CM) to the bind pose and how many edges pass 1.6x (tearing, spikes);
- crush: the smallest ratio and how many edges fall under 0.35x (folding, crumpling into a lump);
- poke: for each layer pair (skin under the jacket, trousers and gloves, trousers under the jacket skirt, the jacket
  under the protector), how many points of the inner layer that were covered at bind come out more than POKE_MM
  through the outer one (show-through).

Solidify is switched off for the measurement (it doubles the surface); masks stay on, so hidden skin is ignored.
"""
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
CLIPS = ROOT / "Resources/Models/Animation/PlaceholderTechniques/PlaceholderTechniques.blend"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
REPORT = Path(args[0]) if args else None
STEP = int(args[1]) if len(args) > 1 else 2
STRETCH, CRUSH, POKE_MM, COVER_MM, MIN_EDGE_CM = 1.6, 0.35, 6.0, 40.0, 0.8
PROTECTOR = "Quilted_Lace_Back__Padded_Torso_Shell"
PAIRS = [("Body", "Jacket"), ("Body", "Pants"), ("Body", "Gloves"), ("Pants", "Jacket_Skirt"), ("Jacket", PROTECTOR)]

rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith("RIG_Body_"))
with bpy.data.libraries.load(str(CLIPS)) as (src, dst):
    dst.actions = [a for a in src.actions if a.startswith("Placeholder_")]
for o in bpy.data.objects:
    for m in o.modifiers:
        if m.type == "SOLIDIFY":
            m.show_viewport = False
        if m.type == "CLOTH":
            m.show_viewport = False
shown = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and not o.name.startswith(("SIM_", "Mat"))
         and any(m.type == "ARMATURE" for m in o.modifiers)]
if not rig.animation_data:
    rig.animation_data_create()


def snapshot():
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for o in shown:
        e = o.evaluated_get(dg)
        m = e.to_mesh()
        mw = o.matrix_world
        out[o.name] = ([mw @ v.co for v in m.vertices], [tuple(ed.vertices) for ed in m.edges],
                       [tuple(p.vertices) for p in m.polygons])
        e.to_mesh_clear()
    return out


def bvh(verts, polys):
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0)


def covered(inner, outer_tree):
    """Indices of inner points that sit under the outer surface (behind it, within COVER_MM)."""
    keep = []
    for i, v in enumerate(inner):
        hit = outer_tree.find_nearest(v, COVER_MM / 1000)
        if hit[0] is not None and (v - hit[0]).dot(hit[1]) < 0:
            keep.append(i)
    return keep


rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()
rest = snapshot()
rest_len = {n: [(vs[a] - vs[b]).length for a, b in es] for n, (vs, es, _) in rest.items()}
cover = {}
for inner, outer in PAIRS:
    if inner in rest and outer in rest:
        cover[(inner, outer)] = covered(rest[inner][0], bvh(rest[outer][0], rest[outer][2]))

report = {"body": rig.name, "clips": {}}
worst = {}
for action in sorted(bpy.data.actions, key=lambda a: a.name):
    if not action.name.startswith("Placeholder_"):
        continue
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    start, end = (int(f) for f in action.frame_range)
    clip = {}
    for frame in range(start, end + 1, STEP):
        bpy.context.scene.frame_set(frame)
        now = snapshot()
        for name, (vs, es, ps) in now.items():
            if len(es) != len(rest_len[name]):
                continue
            lens = [(vs[a] - vs[b]).length for a, b in es]
            # Ratios only on edges long enough to see (MIN_EDGE_CM); tiny edges give meaningless ratios.
            ratios = [n / l for n, l in zip(lens, rest_len[name]) if l > MIN_EDGE_CM / 100] or [1.0]
            s = clip.setdefault(name, {"growth_cm": 0, "stretch": 0, "stretch_edges": 0, "crush": 9, "crush_edges": 0})
            growth = max(n - l for n, l in zip(lens, rest_len[name])) * 100
            hi, lo = max(ratios), min(ratios)
            n_hi = sum(r > STRETCH for r in ratios)
            n_lo = sum(r < CRUSH for r in ratios)
            if growth > s["growth_cm"]:
                s["growth_cm"], s["growth_frame"] = round(growth, 1), frame
            if hi > s["stretch"]:
                s["stretch"], s["stretch_frame"] = round(hi, 2), frame
            if lo < s["crush"]:
                s["crush"], s["crush_frame"] = round(lo, 2), frame
            if n_hi > s["stretch_edges"]:
                s["stretch_edges"], s["stretch_edges_frame"] = n_hi, frame
            if n_lo > s["crush_edges"]:
                s["crush_edges"], s["crush_edges_frame"] = n_lo, frame
        for (inner, outer), idx in cover.items():
            tree = bvh(now[outer][0], now[outer][2])
            pts = now[inner][0]
            n = 0
            for i in idx:
                hit = tree.find_nearest(pts[i], 0.06)
                if hit[0] is not None and (pts[i] - hit[0]).dot(hit[1]) > POKE_MM / 1000:
                    n += 1
            key = f"poke {inner}>{outer}"
            s = clip.setdefault(key, {"points": 0})
            if n > s["points"]:
                s["points"], s["frame"] = n, frame
    report["clips"][action.name] = clip
    for name, s in clip.items():
        w = worst.setdefault(name, {})
        for k, v in s.items():
            if k.endswith("frame"):
                continue
            better = v < w.get(k, (9e9,))[0] if k == "crush" else v > w.get(k, (-1,))[0]
            if better:
                w[k] = (v, action.name)
report["worst"] = worst
text = json.dumps(report, indent=1)
if REPORT:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text)
for name, w in sorted(worst.items()):
    print("WORST", name, " ".join(f"{k}={v[0]}@{v[1].replace('Placeholder_', '')}" for k, v in w.items()))
print("CHECK DONE")
