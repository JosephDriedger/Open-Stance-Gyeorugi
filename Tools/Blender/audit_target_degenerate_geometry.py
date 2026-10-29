"""Inspect a copied mocap target for collapsed geometry and UV triangles; never edit the source."""
import bpy
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / 'Resources/Models/Animation/MotionBuilder_BeltChain/Medium/OpenStance_Medium.fbx'
out = root / 'Resources/Models/FinalRefinement/BeltTargetImportAudit/GeometryDiagnosis'
out.mkdir(parents=True, exist_ok=True)
copy = out / source.name
shutil.copy2(source, copy)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(copy))
rows = []
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    collapsed, uv_collapsed, shape_recoverable = [], 0, 0
    for tri in mesh.loop_triangles:
        a, b, c = [obj.matrix_world @ mesh.vertices[i].co for i in tri.vertices]
        if (b-a).cross(c-a).length < 1e-12:
            collapsed.append(tri.polygon_index)
            if mesh.shape_keys:
                for key in mesh.shape_keys.key_blocks:
                    a, b, c = [obj.matrix_world @ key.data[i].co for i in tri.vertices]
                    if (b-a).cross(c-a).length >= 1e-12:
                        shape_recoverable += 1
                        break
        if mesh.uv_layers.active:
            a, b, c = [mesh.uv_layers.active.data[i].uv.copy() for i in tri.loops]
            u, v = b-a, c-a
            if abs(u.x*v.y-u.y*v.x) < 1e-12:
                uv_collapsed += 1
    rows.append({'mesh': obj.name, 'triangles': len(mesh.loop_triangles),
                 'collapsed_geometry_triangles': len(collapsed),
                 'collapsed_polygon_samples': sorted(set(collapsed))[:20],
                 'shape_keys': len(mesh.shape_keys.key_blocks) if mesh.shape_keys else 0,
                 'collapsed_triangles_with_valid_shape_key': shape_recoverable,
                 'collapsed_uv_triangles': uv_collapsed})
(out / 'validation.json').write_text(json.dumps(rows, indent=2))
print('GEOMETRY_DIAGNOSIS', json.dumps(rows))
