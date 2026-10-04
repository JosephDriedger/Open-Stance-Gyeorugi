"""Reopen creator sources and validate independent wardrobe switches and skin binding."""
import json
import math
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT/'Resources/Models/CreatorFighters'
results = []
try:
    for folder in sorted(p for p in LIB.iterdir() if p.is_dir()):
        filename = folder/f'OpenStance_Creator_{folder.name}.blend'
        bpy.ops.wm.open_mainfile(filepath=str(filename))
        arm, body = bpy.data.objects['root'], bpy.data.objects['Body']
        bones = set(arm.data.bones.keys())
        assert len(bones) == 341
        record = {'body_type':folder.name, 'bones':len(bones), 'switches':{}, 'bindings':{}}
        def update():
            arm.update_tag()
            bpy.context.scene.frame_set(2)
            bpy.context.scene.frame_set(1)
            bpy.context.view_layer.update()
        for part in ('Jacket','Pants','Gloves','FootGuards'):
            for other in ('Jacket','Pants','Gloves','FootGuards'):
                arm[f'Wear_{other}'] = False
            update()
            full = len(body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
            assert full == len(body.data.vertices)
            arm[f'Wear_{part}'] = True
            update()
            covered = len(body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
            assert covered < full, (part,full,covered)
            assert not bpy.data.objects[part].hide_render
            if part == 'Jacket':
                pants = bpy.data.objects['Pants']
                arm['Wear_Pants'] = True
                update()
                shown = len(pants.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
                arm['Wear_Jacket'] = False
                update()
                uncovered = len(pants.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
                assert uncovered > shown, ('Trouser coverage',shown,uncovered)
                record['trouser_overlap'] = {'covered':shown,'uncovered':uncovered,'passed':True}
            arm[f'Wear_{part}'] = False
            update()
            assert bpy.data.objects[part].hide_render
            record['switches'][part] = {'uncovered':full,'covered':covered,'passed':True}
        for name in ('Jacket','Hair_Buzzcut','Protector'):
            obj = bpy.data.objects[name]
            names = {g.index:g.name for g in obj.vertex_groups}
            bad = []
            for v in obj.data.vertices:
                total = sum(g.weight for g in v.groups if names[g.group] in bones)
                if not math.isfinite(total) or abs(total-1) > .002:
                    bad.append(v.index)
            assert not bad, (name, len(bad))
            record['bindings'][name] = {'vertices':len(obj.data.vertices),'normalized':True}
        record['fbx'] = {}
        for mode, count in [('Dobok',6),('Sparring',10)]:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            path = folder/f'OpenStance_Creator_{folder.name}_{mode}.fbx'
            bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
            rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
            meshes = [o for o in bpy.data.objects if o.type == 'MESH']
            assert len(rigs) == 1 and len(rigs[0].data.bones) == 341
            assert len(meshes) == count, (mode,len(meshes))
            assert all(any(m.type == 'ARMATURE' and m.object == rigs[0] for m in o.modifiers) for o in meshes)
            record['fbx'][mode] = {'mesh_count':len(meshes),'single_skeleton':True,'passed':True}
        results.append(record)
    (LIB/'validation.json').write_text(json.dumps({'passed':True,'bodies':results},indent=2))
except Exception:
    import traceback
    (LIB/'validation.json').write_text(json.dumps({'passed':False,'bodies':results,'error':traceback.format_exc()},indent=2))
    raise
