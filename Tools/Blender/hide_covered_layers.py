"""Layer 9 of the traditional dobok: hide the parts of each inner garment that an outer layer always covers.

Every garment is skinned on its own: nothing in a skinned layer knows another garment is there, so once a pose (or the
engine's cloth, which only collides with body capsules) moves two layers differently, the inner one shows through the
outer one. Games avoid that the way the body already is: the covered part of the inner layer is not drawn. This tags,
on each inner garment, the vertices whose outward ray meets the outer layer within REACH, shrinks that set back
ERODE edge rings from the outer layer's edges (so a pose or the cloth's sway cannot open a hole at a rim), stores it as
the vertex group HIDDEN_GROUP and puts an inverted Mask modifier first in the stack (the export applies it).
The protector is measured with its hip-driven hem fold fully on, its smallest coverage.

    blender.exe -b <Candidate.blend> -P hide_covered_layers.py -- <out folder>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
PROTECTOR = ('Quilted_Lace_Back__', 'Smooth_Buckle_Back__')
HIDDEN_GROUP = 'HiddenUnder_OuterLayer'
REACH = .15   # m: a straight-hanging skirt can sit 8+ cm off the trousers at the sides (Compact, Male_Lean)
ERODE = {'Pants': 1, 'Jacket': 3, 'Jacket_Collar': 3}
# The trousers under the skirt are hidden almost to its hem: the engine's skirt cloth sways a little and cannot collide
# with the trousers, so trouser left under the skirt shows through it as patches. The skirt shares the trousers' weights,
# so its hem stays over them in poses and a single ring of margin is enough.

worn_protector = [o for o in scene.objects if o.type == 'MESH' and o.name.startswith(PROTECTOR) and not o.hide_get() and not o.hide_render]
PAIRS = (('Pants', [bpy.data.objects['Jacket_Skirt']]),
         ('Jacket', worn_protector),
         ('Jacket_Collar', worn_protector))

pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
# Smallest protector coverage: hem fold fully on (its drivers are muted while measuring).
muted = []
for obj in worn_protector:
    keys = obj.data.shape_keys
    if not keys:
        continue
    for block in keys.key_blocks:
        if block.name.startswith('HipRetract_Protector_'):
            fc = keys.animation_data.drivers.find('key_blocks["%s"].value' % block.name) if keys.animation_data else None
            if fc:
                fc.mute = True
                muted.append(fc)
            block.value = 1.0
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()


def outer_tree(objects):
    vertices, triangles = [], []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        base = len(vertices)
        vertices += [obj.matrix_world @ v.co for v in mesh.vertices]
        triangles += [tuple(base + i for i in t.vertices) for t in mesh.loop_triangles]
        evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(vertices, triangles, all_triangles=True)


report = {}
for inner_name, outers in PAIRS:
    inner = bpy.data.objects.get(inner_name)
    if inner is None or not outers:
        continue
    tree = outer_tree(outers)
    mesh = inner.data
    world = inner.matrix_world
    normal_matrix = world.to_3x3().inverted().transposed()
    centre = sum((world @ v.co for v in mesh.vertices), Vector()) / len(mesh.vertices)
    covered = set()
    for v in mesh.vertices:
        p = world @ v.co
        n = (normal_matrix @ v.normal).normalized()
        if n.dot(Vector((p.x - centre.x, p.y - centre.y, 0))) < 0:
            n = -n
        if tree.ray_cast(p + n * .001, n, REACH)[0] is not None:
            covered.add(v.index)
    links = defaultdict(list)
    for e in mesh.edges:
        a, b = e.vertices
        links[a].append(b)
        links[b].append(a)
    for _ in range(ERODE.get(inner_name, 3)):
        covered = {i for i in covered if all(j in covered for j in links[i])}
    group = inner.vertex_groups.get(HIDDEN_GROUP) or inner.vertex_groups.new(name=HIDDEN_GROUP)
    group.remove(range(len(mesh.vertices)))
    group.add(sorted(covered), 1.0, 'REPLACE')
    mask = inner.modifiers.get('Hidden under outer layer') or inner.modifiers.new('Hidden under outer layer', 'MASK')
    mask.vertex_group = HIDDEN_GROUP
    mask.invert_vertex_group = True
    with bpy.context.temp_override(object=inner):
        bpy.ops.object.modifier_move_to_index(modifier=mask.name, index=0)
    report[inner_name] = {'hidden_vertices': len(covered), 'of': len(mesh.vertices)}
for fc in muted:
    fc.mute = False
rig.data.pose_position = pose_position
print('HIDDEN LAYERS DONE', json.dumps(report), flush=True)
if OUT:
    (OUT / 'hidden_layers_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
