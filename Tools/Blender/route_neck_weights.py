"""Route neck skin weights through the neck bones (match fighters).

    blender.exe -b Resources/Models/FinalRefinement/Match/<Kind>_<Sex>/Candidate.blend -P route_neck_weights.py -- [--save]

The suite's head mesh (and anything that copied its weights, such as the jacket collar) blends the neck straight from
spine_04 to head, with no weight on neck_01 or neck_02. The placeholder clips turn the head up to 80 degrees from the
chest (neck_01 takes half, head the rest), so a neck vertex halfway between spine_04 and head is averaged across the
whole turn and the neck collapses and stretches like a candy wrapper (head edges up to 6x their bind length in the
spinning kicks).

For every skinned mesh with spine_04 and head weights and no neck weights, each vertex's spine_04 + head share is kept
and only its split changes: with t = head / (spine_04 + head), the share is spread over the chain spine_04 -> neck_01 ->
neck_02 -> head with hat functions at t = 0, 1/3, 2/3, 1. A pure spine_04 vertex (the seam with the body, which has no
neck weights) and a pure head vertex do not change, so the seam stays closed and the face stays rigid; every vertex
keeps the same number of influences (two adjacent chain bones at most replace spine_04 and head).

Importable: route(objects) returns {mesh name: vertices changed}. Prints ROUTE lines.
"""
import sys

import bpy

CHAIN = ("spine_04", "neck_01", "neck_02", "head")


def chain_split(t):
    """Weights over CHAIN for blend parameter t in [0, 1] (hat functions at 0, 1/3, 2/3, 1)."""
    x = min(max(t, 0.0), 1.0) * (len(CHAIN) - 1)
    i = min(int(x), len(CHAIN) - 2)
    f = x - i
    out = [0.0] * len(CHAIN)
    out[i], out[i + 1] = 1.0 - f, f
    return out


def route(objects):
    changed = {}
    for o in objects:
        if o.type != "MESH" or not any(m.type == "ARMATURE" for m in o.modifiers):
            continue
        groups = {g.name: g for g in o.vertex_groups}
        if "spine_04" not in groups or "head" not in groups:
            continue
        idx = {g.index: g.name for g in o.vertex_groups}
        neck_used = False
        rows = []
        for v in o.data.vertices:
            w = {idx[g.group]: g.weight for g in v.groups if idx[g.group] in CHAIN and g.weight > 0}
            if w.get("neck_01", 0) > 0 or w.get("neck_02", 0) > 0:
                neck_used = True
                break
            s, h = w.get("spine_04", 0.0), w.get("head", 0.0)
            if s > 0 and h > 0:
                rows.append((v.index, s + h, h / (s + h)))
        if neck_used or not rows:
            continue
        for n in ("neck_01", "neck_02"):
            if n not in groups:
                groups[n] = o.vertex_groups.new(name=n)
        for i, total, t in rows:
            for name, share in zip(CHAIN, chain_split(t)):
                value = total * share
                if value > 1e-5:
                    groups[name].add([i], value, "REPLACE")
                else:
                    groups[name].remove([i])
        o.data.update()
        changed[o.name] = len(rows)
    return changed


if __name__ == "__main__":
    done = route(list(bpy.data.objects))
    print("ROUTE changed", done, flush=True)
    if "--save" in sys.argv:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_mainfile(compress=True)
        print("ROUTE SAVED", bpy.data.filepath, flush=True)
