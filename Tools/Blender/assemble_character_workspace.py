"""Assemble five clean scenes; archive the previous workspace before replacement."""
from pathlib import Path
import hashlib,json,shutil,traceback
import bpy

ROOT=Path(__file__).resolve().parents[2]
MODELS=ROOT/'Resources/Models'
ANIM=MODELS/'Animation'
DEST=MODELS/'OpenStance_Characters_Workspace.blend'
BACKUP=MODELS/'Archive/Pre_Animation_Workspace'
REPORT=ANIM/'workspace_validation.json'
try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    default=bpy.context.scene
    reports=[]
    for kind in ['Compact','Medium','Stocky','LeanTall','Tall']:
        source=ANIM/f'OpenStance_{kind}_Animation.blend'
        with bpy.data.libraries.load(str(source),link=False) as (src,dst):
            dst.scenes=[f'Fighter_{kind}']
        scene=dst.scenes[0]
        assert scene is not None
        for coll in scene.collection.children:coll.name=f'{kind}_{coll.name}'
        for obj in scene.objects:
            if not obj.name.startswith('RIG_'):obj.name=f'{kind}_{obj.name.split(".")[0]}'
        rig=next(o for o in scene.objects if o.name==f'RIG_Body_{kind}')
        face=next(o for o in scene.objects if o.name==f'RIG_Face_{kind}')
        assert len(rig.data.bones)==341 and len(face.data.bones)==874
        guides=[o for o in scene.objects if o.get('MarkerLabel')]
        assert len(guides)==41
        assert all(o.parent==rig for o in guides)
        scene['WorkspaceVersion']='OpenStance_Animation_2026-10-02'
        reports.append({'body_type':kind,'scene':scene.name,'body_bones':341,'face_bones':874,'marker_labels':sorted(o['MarkerLabel'] for o in guides),'mesh_parts':sorted(o.name for o in scene.objects if o.type=='MESH' and not o.name.endswith(('Mat','MatBorder')))})
    bpy.context.window.scene=bpy.data.scenes['Fighter_Medium']
    bpy.data.scenes.remove(default)
    for img in bpy.data.images:
        if img.source=='FILE' and not img.packed_file:
            img.pack()
    if 'START_HERE.txt' not in bpy.data.texts:
        bpy.data.texts.new('START_HERE.txt').write((ANIM/'README.md').read_text())
    rig=bpy.data.objects['RIG_Body_Medium']
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    # A copy retains every old referee/environment/character scene; no source dependencies are moved.
    backup_path=BACKUP/DEST.name
    if DEST.exists() and not backup_path.exists():
        BACKUP.mkdir(parents=True,exist_ok=True)
        shutil.copy2(DEST,backup_path)
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        assert digest(DEST)==digest(backup_path)
        (BACKUP/'archive_manifest.json').write_text(json.dumps({'original':str(DEST),'backup':str(backup_path),'sha256':digest(backup_path),'reason':'Superseded active workspace; preserved with referees and environment.'},indent=2))
        (BACKUP/'README.md').write_text('This is the prior character workspace, preserved intact before replacement. It contains legacy fighters, referees and environment scenes. Open it separately to recover any asset. The active workspace is ../../OpenStance_Characters_Workspace.blend. Legacy pipeline input files elsewhere remain in place.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST),compress=True)
    # Reopen the actual deliverable and check dependency/driver persistence.
    bpy.ops.wm.open_mainfile(filepath=str(DEST))
    for kind in ['Compact','Medium','Stocky','LeanTall','Tall']:
        scene=bpy.data.scenes[f'Fighter_{kind}'];bpy.context.window.scene=scene
        rig=bpy.data.objects[f'RIG_Body_{kind}']
        body=bpy.data.objects[f'{kind}_Body']
        face=bpy.data.objects[f'RIG_Face_{kind}']
        assert len(rig.animation_data.nla_tracks)==3
        for bone in face.pose.bones:
            for c in bone.constraints:
                assert c.target==rig
        for obj in scene.objects:
            if obj.type=='MESH' and obj.name.split('_',1)[-1] not in ('Mat','MatBorder'):
                assert any(m.type=='ARMATURE' for m in obj.modifiers),obj.name
        for part in ['Jacket','Pants','Gloves','FootGuards']:rig['Wear_'+part]=False
        rig.update_tag();scene.frame_set(2);scene.frame_set(1);bpy.context.view_layer.update()
        assert len(body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)==len(body.data.vertices)
        for part in ['Jacket','Pants']:rig['Wear_'+part]=True
        rig.update_tag();bpy.context.view_layer.update()
    # This reopen is validation-only: the already-saved file retains its original default wardrobe.
    REPORT.write_text(json.dumps({'passed':True,'source_archive':str(backup_path),'scenes':reports,'real_capture_solve_verified':False},indent=2))
except Exception:
    REPORT.write_text(json.dumps({'passed':False,'error':traceback.format_exc()},indent=2));raise
