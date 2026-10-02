"""Shared procedural prop builder for the venue meshes (build_environment_meshes, build_venue_meshes).

Conventions: metres, origin at the bottom centre, front of the prop faces -Y. UVs are world-scale
(1 UV unit = 1 m) except "Screen"/"Canvas" slots, which get 0-1 UVs for their textures.
Each Builder exports Resources/Environment/Meshes/<name>.fbx in centimetres; material slot names
(MI_*) are matched to material instances by the Unreal level scripts.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector
import rig_config as cfg

OUT_DIR = os.path.join(os.path.dirname(cfg.OUTPUT_DIR), "Environment", "Meshes")


def environment_scene():
    """Switch to an empty "Environment" scene (the fighter scene is untouched); returns the previous scene."""
    os.makedirs(OUT_DIR, exist_ok=True)
    previous = bpy.context.window.scene
    scene = bpy.data.scenes.get("Environment") or bpy.data.scenes.new("Environment")
    bpy.context.window.scene = scene
    for o in list(scene.collection.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return previous


def octagon(flat_to_flat):
    r = flat_to_flat / 2 / math.cos(math.radians(22.5))
    return [(r * math.cos(math.radians(22.5 + 45 * k)), r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]


class Builder:
    log = print   # scripts point this at their log file
    CHUNK = 1500  # bmesh primitive ops slow down as the bmesh grows, so big props are built in chunks

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.slots = []
        self.canvas_faces = set()
        self.canvas_info = {}
        self.chunks = []

    def _rollover(self):
        """Move the current geometry (UVs done) into a chunk mesh and start an empty bmesh."""
        if len(self.bm.faces) < self.CHUNK:
            return
        me = bpy.data.meshes.new(f"{self.name}_chunk")
        self._uv_and_write(me)
        self.chunks.append(me)
        self.bm = bmesh.new()
        self.canvas_faces, self.canvas_info = set(), {}

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
        self._rollover()
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
        self._rollover()
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
        self._rollover()
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
        return self._quad(loc, right, up, w, h, facing, mat)

    def floor_canvas(self, w, h, loc, mat):
        """Upward-facing quad with 0-1 UVs: U along +X, V along +Y."""
        return self._quad(loc, Vector((1, 0, 0)), Vector((0, 1, 0)), w, h, Vector((0, 0, 1)), mat)

    def _quad(self, loc, right, up, w, h, facing, mat):
        self._rollover()
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
        self._rollover()
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

    def _uv_and_write(self, me):
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
        bm.to_mesh(me)
        bm.free()

    def finish(self):
        me = bpy.data.meshes.new(self.name)
        self._uv_and_write(me)
        if self.chunks:   # merge the chunks: from_mesh appends to a bmesh's existing geometry
            bm = bmesh.new()
            for part in self.chunks + [me]:
                bm.from_mesh(part)
            bm.to_mesh(me)
            bm.free()
            for part in self.chunks:
                bpy.data.meshes.remove(part)
        for s in self.slots:
            mat = bpy.data.materials.get(s) or bpy.data.materials.new(s)
            me.materials.append(mat)
        scene = bpy.context.window.scene
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
        Builder.log(self.name, "faces", len(me.polygons), "slots", self.slots)
        return obj
