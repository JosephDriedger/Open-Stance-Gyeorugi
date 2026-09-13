"""Bake MetaHuman body hidden face maps for the fitted dobok and gear.

Run after fit_to_body in the same scene:

    run("hidden_face_maps", TARGET_NAME="MH_FighterBase_Body")

For each garment, body skin that the garment covers is painted black in body UV space
(T_HFM_<Part>.png, 1024x1024, linear). Unreal's MetaHuman pipeline removes body triangles fully
under black pixels when that wardrobe item is worn, so skin can't poke through the cloth when
animation bends the body (elbows, hips, shoulders). Coverage is eroded back from garment
openings (cuffs, collar, hems) so no gaps show where the cloth slides.
"""
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import rig_config as cfg

log = cfg.open_log("hidden_face_maps")

SIZE = 1024
# max_gap: how far (m) outside the skin the garment may be and still count as covering it.
# erode: vertex rings kept visible next to uncovered skin (openings).
PARTS = {
    "Jacket":     dict(max_gap=0.10, erode=3),
    "Pants":      dict(max_gap=0.10, erode=3),
    "Gloves":     dict(max_gap=0.03, erode=1),
    "FootGuards": dict(max_gap=0.03, erode=1),
}

target_name = globals().get("TARGET_NAME", "MH_FighterBase_Body")
coll = bpy.data.collections[globals().get("COLLECTION", f"Target_{target_name}")]
body = max((o for o in coll.objects if o.type == 'MESH' and o.name.startswith(target_name)),
           key=lambda o: len(o.data.vertices))
out_dir = globals().get("OUT_DIR", os.path.join(cfg.OUTPUT_DIR, "Fitted", target_name))
PART_PREFIX = globals().get("PART_PREFIX", "SK_Fighter_")
PARTS = globals().get("PART_SETTINGS") or PARTS   # override, e.g. {"Shirt": dict(max_gap=0.08, erode=3)}

arm = body.find_armature() or body.parent
saved_pose = None
if arm:
    saved_pose = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()


def world_bm(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    bm.from_object(obj, dg)
    bm.transform(obj.matrix_world)
    bm.normal_update()
    return bm


try:
    body_bm = world_bm(body)
    body_bm.verts.ensure_lookup_table()
    body_bm.faces.ensure_lookup_table()
    uv_layer = body_bm.loops.layers.uv.active
    nbrs = [[e.other_vert(v).index for e in v.link_edges] for v in body_bm.verts]

    for pname, s in PARTS.items():
        stem = f"{PART_PREFIX}{pname}"
        part = next((o for o in coll.objects if o.type == 'MESH' and o.name.startswith(stem)
                     and o.name[len(stem):len(stem) + 1] in ("", "_", ".")), None)   # "SK_X_Shirt", "_Body", ".001"
        if part is None:
            log("no fitted part", pname)
            continue
        pbm = world_bm(part)
        bvh = BVHTree.FromBMesh(pbm)
        pbm.free()

        covered = np.zeros(len(body_bm.verts), dtype=bool)
        for v in body_bm.verts:
            n = v.normal
            if n.length < 1e-6:
                continue
            origin = v.co - n * 0.002
            hit = bvh.ray_cast(origin, n, s["max_gap"])
            covered[v.index] = hit[0] is not None
        # keep skin visible next to uncovered skin (openings)
        hidden = covered.copy()
        for _ in range(s["erode"]):
            nxt = hidden.copy()
            for i in np.nonzero(hidden)[0]:
                if any(not hidden[j] for j in nbrs[i]):
                    nxt[i] = False
            hidden = nxt

        img = np.ones((SIZE, SIZE), dtype=np.float32)
        faces_hidden = 0
        for f in body_bm.faces:
            if not all(hidden[v.index] for v in f.verts):
                continue
            faces_hidden += 1
            uvs = [l[uv_layer].uv for l in f.loops]
            for k in range(1, len(uvs) - 1):
                # MetaHuman body UVs live in UDIM tile 1002 (u 1..2); Unreal wraps them to 0..1
                tri = np.mod(np.array([uvs[0], uvs[k], uvs[k + 1]], dtype=np.float64), 1.0) * SIZE
                x0, y0 = np.floor(tri.min(axis=0)).astype(int) - 1
                x1, y1 = np.ceil(tri.max(axis=0)).astype(int) + 1
                x0, y0 = max(x0, 0), max(y0, 0)
                x1, y1 = min(x1, SIZE - 1), min(y1, SIZE - 1)
                if x1 < x0 or y1 < y0:
                    continue
                xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
                (ax, ay), (bx, by), (cx, cy) = tri
                d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(d) < 1e-12:
                    continue
                w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
                w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
                w2 = 1.0 - w0 - w1
                # half-pixel slack so shared edges between hidden faces leave no white seams
                slack = 0.75 / max(np.ptp(tri[:, 0]), np.ptp(tri[:, 1]), 1.0)
                inside = (w0 >= -slack) & (w1 >= -slack) & (w2 >= -slack)
                img[y0:y1 + 1, x0:x1 + 1][inside] = 0.0

        name = f"T_HFM_{pname}"
        bimg = bpy.data.images.get(name) or bpy.data.images.new(name, SIZE, SIZE, alpha=False)
        bimg.colorspace_settings.name = 'Non-Color'
        rgba = np.stack([img, img, img, np.ones_like(img)], axis=-1)   # row 0 = v 0 (bottom)
        bimg.pixels.foreach_set(rgba.ravel())
        path = os.path.join(out_dir, f"{name}.png")
        bimg.filepath_raw = path
        bimg.file_format = 'PNG'
        bimg.save()
        log(pname, "covered verts", int(covered.sum()), "hidden verts", int(hidden.sum()),
            "hidden faces", faces_hidden, "->", path)
    body_bm.free()
finally:
    if arm and saved_pose:
        for pb in arm.pose.bones:
            pb.matrix_basis = saved_pose[pb.name]
        bpy.context.view_layer.update()
log.close()
