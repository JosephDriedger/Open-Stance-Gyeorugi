"""Prop meshes for the sparring venues (competition arena, training dojang).

    run("build_environment_meshes")

Builds each prop procedurally in a separate "Environment" scene (the fighter scene is untouched)
and exports Resources/Environment/Meshes/SM_<Name>.fbx in centimetres. Material slot names
(MI_*) are matched to material instances by Tools/Unreal/build_arenas.py.

Conventions: metres, origin at the bottom centre, front of the prop faces -Y. UVs are world-scale
(1 UV unit = 1 m) except "Screen"/"Canvas" slots, which get 0-1 UVs for their textures.
Real-world sizes: WT competition mat = 8 m octagon (flat to flat) inside a 12 m x 12 m square,
1 m interlocking tiles, 4 cm thick.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector
import rig_config as cfg

log = cfg.open_log("build_environment_meshes")
OUT_DIR = os.path.join(os.path.dirname(cfg.OUTPUT_DIR), "Environment", "Meshes")
os.makedirs(OUT_DIR, exist_ok=True)

previous_scene = bpy.context.window.scene
scene = bpy.data.scenes.get("Environment") or bpy.data.scenes.new("Environment")
bpy.context.window.scene = scene
for o in list(scene.collection.objects):
    bpy.data.objects.remove(o, do_unlink=True)


class Builder:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.slots = []
        self.canvas_faces = set()
        self.canvas_info = {}

    def slot(self, mat):
        if mat not in self.slots:
            self.slots.append(mat)
        return self.slots.index(mat)

    def _tag(self, geom, mat, canvas=False):
        idx = self.slot(mat)
        faces = [g for g in geom if isinstance(g, bmesh.types.BMFace)]
        for f in faces:
            f.material_index = idx
            if canvas:
                self.canvas_faces.add(f)
        return faces

    def box(self, size, loc, mat, rot_z=0.0, rot=None):
        """size (x, y, z); loc = centre of the box."""
        res = bmesh.ops.create_cube(self.bm, size=1.0)
        verts = res["verts"]
        m = Matrix.Translation(loc)
        if rot is not None:
            m = m @ rot
        elif rot_z:
            m = m @ Matrix.Rotation(rot_z, 4, 'Z')
        m = m @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
        bmesh.ops.transform(self.bm, matrix=m, verts=verts)
        return self._tag({f for v in verts for f in v.link_faces}, mat)

    def cyl(self, r, h, loc, mat, seg=16, r2=None, rot=None):
        """Cylinder/cone along Z; loc = centre of the base."""
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=r,
                                    radius2=r if r2 is None else r2, depth=h)
        verts = res["verts"]
        m = Matrix.Translation(loc)
        if rot is not None:
            m = m @ rot
        m = m @ Matrix.Translation((0, 0, h / 2))
        bmesh.ops.transform(self.bm, matrix=m, verts=verts)
        return self._tag({f for v in verts for f in v.link_faces}, mat)

    def rod(self, p1, p2, r, mat, seg=8):
        p1, p2 = Vector(p1), Vector(p2)
        d = p2 - p1
        rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
        return self.cyl(r, d.length, p1, mat, seg=seg, rot=rot)

    def sphere(self, r, loc, mat, scale=(1, 1, 1), seg=12):
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=seg // 2 + 2, radius=r)
        verts = res["verts"]
        bmesh.ops.transform(self.bm, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((*scale, 1)), verts=verts)
        return self._tag({f for v in verts for f in v.link_faces}, mat)

    def canvas(self, w, h, loc, mat, facing=Vector((0, -1, 0))):
        """Single quad (0-1 UVs, image upright as seen from the front) centred at loc, facing `facing`
        (horizontal directions only)."""
        facing = Vector(facing).normalized()
        up = Vector((0, 0, 1))
        right = facing.cross(up).normalized() * -1   # viewer's right when looking at the front
        loc = Vector(loc)
        pts = [loc - right * w / 2 - up * h / 2, loc + right * w / 2 - up * h / 2,
               loc + right * w / 2 + up * h / 2, loc - right * w / 2 + up * h / 2]
        verts = [self.bm.verts.new(p) for p in pts]
        f = self.bm.faces.new(verts)
        f.normal_update()
        if f.normal.dot(facing) < 0:
            f.normal_flip()
        self.canvas_info[f] = (loc, right, up, w, h)
        return self._tag([f], mat, canvas=True)

    def prism(self, outline, z0, z1, mat):
        """Extrude a closed XY outline (convex or simple polygon) from z0 to z1."""
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]))
        if area < 0:
            outline = list(reversed(outline))   # counter-clockwise so the faces point outward
        bot = [self.bm.verts.new((x, y, z0)) for x, y in outline]
        top = [self.bm.verts.new((x, y, z1)) for x, y in outline]
        faces = [self.bm.faces.new(top), self.bm.faces.new(list(reversed(bot)))]
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            faces.append(self.bm.faces.new([bot[i], bot[j], top[j], top[i]]))
        return self._tag(faces, mat)

    def finish(self):
        bm = self.bm
        bm.normal_update()   # primitives are built with outward winding; no recalculation (canvases are single quads)
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            if f in self.canvas_info:
                loc, right, up, w, h = self.canvas_info[f]
                for l in f.loops:
                    d = l.vert.co - loc
                    l[uv].uv = (d.dot(right) / w + 0.5, d.dot(up) / h + 0.5)
                continue
            n = f.normal
            ax = max(range(3), key=lambda k: abs(n[k]))
            for l in f.loops:
                co = l.vert.co
                l[uv].uv = (co.x, co.y) if ax == 2 else ((co.x, co.z) if ax == 1 else (co.y, co.z))
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for s in self.slots:
            mat = bpy.data.materials.get(s) or bpy.data.materials.new(s)
            me.materials.append(mat)
        obj = bpy.data.objects.new(self.name, me)
        scene.collection.objects.link(obj)
        for o in scene.objects:
            o.select_set(o == obj)
        bpy.context.view_layer.objects.active = obj
        path = os.path.join(OUT_DIR, f"{self.name}.fbx")
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'},
                                 apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
                                 axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE',
                                 use_mesh_modifiers=False, bake_anim=False, path_mode='STRIP')
        log(self.name, "faces", len(me.polygons), "slots", self.slots)
        return obj


# ---------------------------------------------------------------- competition area
def octagon(flat_to_flat):
    r = flat_to_flat / 2 / math.cos(math.radians(22.5))
    return [(r * math.cos(math.radians(22.5 + 45 * k)), r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]


MAT_T = 0.04
b = Builder("SM_MatOctagon")
b.prism(octagon(8.0), 0.0, MAT_T, "MI_MatBlue")
b.finish()

# Red square (12 m) minus the octagon: 8 segments, pentagons where a square corner falls inside.
b = Builder("SM_MatSquareBorder")
oct_pts = octagon(8.0)
half = 6.0


def square_point(angle_deg):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    k = half / max(abs(c), abs(s))
    return (c * k, s * k)


for k in range(8):
    a0, a1 = 22.5 + 45 * k, 22.5 + 45 * (k + 1)
    ring = [oct_pts[k], oct_pts[(k + 1) % 8], square_point(a1)]
    mid = 45 * (k + 1)
    if mid % 90 == 45:   # a square corner lies in this sector
        ring.append((half * math.copysign(1, math.cos(math.radians(mid))), half * math.copysign(1, math.sin(math.radians(mid)))))
    ring.append(square_point(a0))
    b.prism(ring, 0.0, MAT_T, "MI_MatRed")
b.finish()

# Box truss, 4 m, 30 cm section
b = Builder("SM_Truss4m")
s, L, rc, rl = 0.15, 4.0, 0.024, 0.01
chords = [(-s, -s), (s, -s), (s, s), (-s, s)]
for cx, cz in chords:
    b.rod((-L / 2, cx, cz), (L / 2, cx, cz), rc, "MI_TrussMetal", seg=10)
steps = 8
for i in range(steps):
    x0, x1 = -L / 2 + i * L / steps, -L / 2 + (i + 1) * L / steps
    for (ay, az), (by_, bz) in zip(chords, chords[1:] + chords[:1]):
        b.rod((x0, ay, az), (x1, by_, bz), rl, "MI_TrussMetal", seg=6)
        b.rod((x0, ay, az), (x0, by_, bz), rl, "MI_TrussMetal", seg=6)
b.finish()

# Stage spotlight fixture (hangs below a truss)
b = Builder("SM_SpotFixture")
b.cyl(0.13, 0.35, (0, 0, -0.45), "MI_BlackPlastic", seg=16, r2=0.16)
b.cyl(0.12, 0.01, (0, 0, -0.46), "MI_LightLens", seg=16)
b.box((0.36, 0.03, 0.3), (0, 0.18, -0.25), "MI_BlackPlastic")
b.box((0.36, 0.03, 0.3), (0, -0.18, -0.25), "MI_BlackPlastic")
b.box((0.06, 0.06, 0.12), (0, 0, -0.05), "MI_BlackPlastic")
b.finish()

# Judge / recorder table with black cloth drape, 1.8 m
b = Builder("SM_JudgeTable")
b.box((1.8, 0.7, 0.03), (0, 0, 0.745), "MI_TableCloth")
b.box((1.8, 0.02, 0.72), (0, -0.34, 0.38), "MI_TableCloth")
b.box((0.02, 0.7, 0.72), (-0.89, 0, 0.38), "MI_TableCloth")
b.box((0.02, 0.7, 0.72), (0.89, 0, 0.38), "MI_TableCloth")
for x in (-0.85, 0.85):
    for y in (-0.3, 0.3):
        b.cyl(0.02, 0.73, (x, y, 0), "MI_TrussMetal", seg=8)
b.finish()

# Office chair (officials)
b = Builder("SM_ChairOffice")
b.box((0.48, 0.46, 0.08), (0, 0, 0.47), "MI_BlackFabric")
b.box((0.46, 0.06, 0.52), (0, 0.24, 0.8), "MI_BlackFabric", rot=Matrix.Rotation(math.radians(-8), 4, 'X'))
b.cyl(0.03, 0.36, (0, 0, 0.08), "MI_BlackPlastic", seg=10)
for k in range(5):
    a = math.radians(90 + 72 * k)
    b.rod((0, 0, 0.08), (0.3 * math.cos(a), 0.3 * math.sin(a), 0.05), 0.02, "MI_BlackPlastic", seg=6)
    b.sphere(0.03, (0.3 * math.cos(a), 0.3 * math.sin(a), 0.03), "MI_BlackPlastic")
for x in (-0.26, 0.26):
    b.box((0.04, 0.3, 0.03), (x, 0.02, 0.67), "MI_BlackPlastic")
    b.box((0.03, 0.03, 0.18), (x, 0.1, 0.58), "MI_BlackPlastic")
b.finish()

# Stacking chair with coloured shell (coach chairs are blue / red)
for colour in ("Blue", "Red", "Black"):
    b = Builder(f"SM_ChairStack{colour}")
    shell = f"MI_Plastic{colour}"
    b.box((0.46, 0.44, 0.04), (0, 0, 0.45), shell)
    b.box((0.46, 0.04, 0.42), (0, 0.23, 0.72), shell, rot=Matrix.Rotation(math.radians(-10), 4, 'X'))
    for x in (-0.2, 0.2):
        for y in (-0.19, 0.19):
            b.cyl(0.012, 0.45, (x, y, 0), "MI_TrussMetal", seg=8)
    b.finish()

# Stadium seat row: 10 fold-down seats, 0.5 m pitch
b = Builder("SM_SeatRow10")
for i in range(10):
    x = -2.25 + i * 0.5
    b.box((0.44, 0.42, 0.05), (x, 0, 0.44), "MI_SeatDark")
    b.box((0.44, 0.05, 0.42), (x, 0.22, 0.72), "MI_SeatDark", rot=Matrix.Rotation(math.radians(-12), 4, 'X'))
    b.box((0.04, 0.4, 0.44), (x - 0.25, 0.02, 0.22), "MI_TrussMetal")
b.box((0.04, 0.4, 0.44), (2.5, 0.02, 0.22), "MI_TrussMetal")
b.finish()

# Monitor on a stand
b = Builder("SM_Monitor")
b.box((0.56, 0.04, 0.36), (0, 0, 0.3), "MI_BlackPlastic")
b.canvas(0.52, 0.31, (0, -0.021, 0.3), "MI_ScreenDark")
b.box((0.05, 0.05, 0.14), (0, 0.03, 0.07), "MI_BlackPlastic")
b.box((0.22, 0.16, 0.015), (0, 0.02, 0.0075), "MI_BlackPlastic")
b.finish()

# Desk microphone (gooseneck)
b = Builder("SM_DeskMic")
b.cyl(0.05, 0.02, (0, 0, 0), "MI_BlackPlastic", seg=16)
b.rod((0, 0, 0.02), (0, -0.06, 0.28), 0.006, "MI_BlackPlastic", seg=6)
b.cyl(0.012, 0.07, (0, -0.06, 0.28), "MI_BlackPlastic", seg=10, rot=Matrix.Rotation(math.radians(-60), 4, 'X'))
b.finish()

# Water bucket and towel (coach corner)
b = Builder("SM_Bucket")
b.cyl(0.12, 0.28, (0, 0, 0), "MI_PlasticRed", seg=20, r2=0.15)
b.finish()
b = Builder("SM_TowelFolded")
b.box((0.36, 0.24, 0.05), (0, 0, 0.025), "MI_TowelWhite")
b.finish()

# Scoreboard screen (16:6.4), 4 m wide
b = Builder("SM_Scoreboard")
b.box((4.2, 0.35, 1.8), (0, 0.18, 0.9), "MI_BlackPlastic")
b.canvas(4.0, 1.6, (0, -0.001, 0.9), "MI_ScreenScoreboard")
b.finish()

# ---------------------------------------------------------------- training dojang
# Free-standing heavy bag
b = Builder("SM_HeavyBagStanding")
b.cyl(0.32, 0.45, (0, 0, 0), "MI_BlackPlastic", seg=24, r2=0.26)
b.cyl(0.19, 1.25, (0, 0, 0.45), "MI_BlackVinyl", seg=24)
b.cyl(0.195, 0.08, (0, 0, 1.2), "MI_PlasticRed", seg=24)
b.cyl(0.195, 0.03, (0, 0, 1.36), "MI_TrussMetal", seg=24)
b.sphere(0.19, (0, 0, 1.7), "MI_BlackVinyl", scale=(1, 1, 0.25), seg=16)
b.finish()

# Double kick paddle
b = Builder("SM_KickPaddle")
for x in (-0.07, 0.07):
    b.cyl(0.1, 0.03, (x, 0, 0.0), "MI_BlackVinyl", seg=16, rot=Matrix.Translation((0, 0, 0.25)) @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Diagonal((0.7, 1.2, 1, 1)))
b.box((0.04, 0.03, 0.14), (0, 0, 0.07), "MI_PlasticRed")
b.finish()

# Kick target shield
b = Builder("SM_TargetShield")
b.box((0.42, 0.14, 0.62), (0, 0, 0.31), "MI_BlackVinyl")
b.box((0.3, 0.005, 0.18), (0, -0.0725, 0.43), "MI_PlasticRed")
b.finish()

# Wall rack board with pegs (1.4 m)
b = Builder("SM_WallRack")
b.box((1.4, 0.03, 1.4), (0, 0.015, 0.7), "MI_WoodLight")
for row in range(3):
    for col in range(5):
        b.rod((-0.56 + col * 0.28, 0, 1.15 - row * 0.42), (-0.56 + col * 0.28, -0.12, 1.2 - row * 0.42), 0.01, "MI_TrussMetal", seg=6)
b.finish()

# Dobok on a hanger
b = Builder("SM_DobokHanging")
b.rod((-0.2, 0, 1.0), (0.2, 0, 1.0), 0.006, "MI_TrussMetal", seg=6)
b.box((0.46, 0.06, 0.62), (0, 0, 0.66), "MI_DobokWhite")
b.box((0.16, 0.06, 0.5), (-0.3, 0, 0.72), "MI_DobokWhite", rot=Matrix.Rotation(math.radians(12), 4, 'Y'))
b.box((0.16, 0.06, 0.5), (0.3, 0, 0.72), "MI_DobokWhite", rot=Matrix.Rotation(math.radians(-12), 4, 'Y'))
b.box((0.2, 0.065, 0.06), (0, 0, 0.93), "MI_BlackFabric")
b.box((0.48, 0.065, 0.05), (0, 0, 0.44), "MI_BlackFabric")
b.box((0.44, 0.05, 0.4), (0, 0.01, 0.16), "MI_DobokWhite")
b.finish()

# Shoe cubby: 4 columns x 3 rows, 1.2 m wide
b = Builder("SM_ShoeCubby")
W_, D_, H_ = 1.2, 0.35, 1.0
b.box((W_, D_, 0.02), (0, 0, 0.01), "MI_WoodMid")
for r in range(1, 4):
    b.box((W_, D_, 0.02), (0, 0, r * H_ / 3), "MI_WoodMid")
for c in range(5):
    b.box((0.02, D_, H_), (-W_ / 2 + c * W_ / 4, 0, H_ / 2), "MI_WoodMid")
b.box((W_, 0.01, H_), (0, D_ / 2, H_ / 2), "MI_WoodMid")
for r in range(3):
    for c in range(4):
        if (r + c) % 3 != 2:
            b.box((0.2, 0.28, 0.1), (-W_ / 2 + (c + 0.5) * W_ / 4, -0.02, r * H_ / 3 + 0.07), "MI_BlackVinyl" if (r * 4 + c) % 2 else "MI_PlasticRed")
b.finish()

# Bench, 1.6 m
b = Builder("SM_Bench")
b.box((1.6, 0.36, 0.05), (0, 0, 0.44), "MI_WoodLight")
for x in (-0.7, 0.7):
    b.box((0.05, 0.3, 0.42), (x, 0, 0.21), "MI_BlackPlastic")
b.finish()

# Potted plant
b = Builder("SM_PlantPot")
b.cyl(0.18, 0.4, (0, 0, 0), "MI_PotWhite", seg=20, r2=0.21)
for k in range(14):
    a = math.radians(k * 137.5)
    rr = 0.08 + 0.02 * (k % 3)
    top = (math.cos(a) * 0.35, math.sin(a) * 0.35, 1.0 + 0.25 * ((k * 7) % 5) / 5)
    b.rod((math.cos(a) * rr * 0.3, math.sin(a) * rr * 0.3, 0.38), top, 0.008, "MI_PlantGreen", seg=5)
    b.sphere(0.12, top, "MI_PlantGreen", scale=(1.2, 0.5, 0.35), seg=8)
b.finish()

# Wall-mounted padding panel (1 m x 0.6 m, sits at floor along the mirror wall)
b = Builder("SM_WallPad")
b.box((1.0, 0.1, 0.6), (0, 0, 0.3), "MI_PadBlue")
b.finish()

# Framed picture, 1.2 m x 0.9 m (canvas slot takes the artwork)
for nm, (w, h) in (("SM_FrameLandscape", (1.2, 0.9)), ("SM_FrameFlag", (1.5, 1.0))):
    b = Builder(nm)
    t = 0.05
    b.box((w + 2 * t, 0.04, t), (0, 0, h / 2 + t / 2), "MI_WoodMid")
    b.box((w + 2 * t, 0.04, t), (0, 0, -h / 2 - t / 2), "MI_WoodMid")
    b.box((t, 0.04, h), (-w / 2 - t / 2, 0, 0), "MI_WoodMid")
    b.box((t, 0.04, h), (w / 2 + t / 2, 0, 0), "MI_WoodMid")
    b.box((w, 0.01, h), (0, 0.015, 0), "MI_PotWhite")
    b.canvas(w, h, (0, 0.009, 0), "MI_Canvas")
    b.finish()

# Door with frame, vision slit and handle (0.95 x 2.1 m)
b = Builder("SM_Door")
b.box((0.95, 0.05, 2.1), (0, 0, 1.05), "MI_WoodMid")
b.box((0.12, 0.052, 0.6), (0.25, 0, 1.45), "MI_Glass")
for x in (-0.53, 0.53):
    b.box((0.1, 0.12, 2.2), (x, 0, 1.1), "MI_WoodLight")
b.box((1.16, 0.12, 0.1), (0, 0, 2.15), "MI_WoodLight")
b.box((0.14, 0.04, 0.02), (-0.36, -0.05, 1.0), "MI_TrussMetal")
b.finish()

# Exit sign
b = Builder("SM_ExitSign")
b.box((0.36, 0.05, 0.16), (0, 0.025, 0.08), "MI_BlackPlastic")
b.canvas(0.34, 0.14, (0, -0.001, 0.08), "MI_ScreenExit")
b.finish()

# Window unit 1.8 m x 2.6 m: frame + mullions + glass
b = Builder("SM_Window")
Wn, Hn, t = 1.8, 2.6, 0.08
for z in (0, Hn):
    b.box((Wn, 0.14, t), (0, 0, z), "MI_FrameDark")
for x in (-Wn / 2, 0, Wn / 2):
    b.box((t, 0.14, Hn), (x, 0, Hn / 2), "MI_FrameDark")
b.box((Wn, 0.14, t * 0.7), (0, 0, Hn * 0.62), "MI_FrameDark")
b.box((Wn, 0.01, Hn), (0, 0.02, Hn / 2), "MI_Glass")
b.finish()

# Linear LED ceiling fixture 1.2 m
b = Builder("SM_LedLinear")
b.box((1.2, 0.12, 0.05), (0, 0, -0.025), "MI_TrussMetal")
b.box((1.18, 0.1, 0.01), (0, 0, -0.055), "MI_LightPanel")
b.finish()

log("DONE", OUT_DIR)
log.close()
bpy.context.window.scene = previous_scene
