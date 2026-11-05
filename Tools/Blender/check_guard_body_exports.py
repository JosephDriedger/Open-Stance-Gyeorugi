"""Independent Blender reimport checks for complete guard delivery FBXs."""
import bpy,sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
OUT=review.ROOT/'Resources/Models/FinalRefinement/GuardBodyDelivery'
manifest=json.loads((OUT/'exports.json').read_text());assert len(manifest['exports'])==18
report=dict(production_installed=False,checks=[])
for entry in manifest['exports']:
    kind=entry['preset'];style=entry['style'];path=OUT/entry['file']
    bpy.ops.wm.open_mainfile(filepath=str(review.ROOT/f'Resources/Models/FinalRefinement/GuardBodyVariantsV7/{kind}/Gameplay_High_Staged.blend'))
    native=bpy.data.objects['RIG_Body_'+kind]
    reference={b.name:b.parent.name if b.parent else None for b in native.data.bones}
    for obj in list(bpy.context.scene.objects):
        if obj.type=='ARMATURE' or (obj.type=='MESH' and any(m.type=='ARMATURE' for m in obj.modifiers)):bpy.data.objects.remove(obj,do_unlink=True)
    before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    objects=[o for o in bpy.context.scene.objects if o not in before];rigs=[o for o in objects if o.type=='ARMATURE'];assert len(rigs)==1
    rig=rigs[0];assert reference=={b.name:b.parent.name if b.parent else None for b in rig.data.bones},kind
    meshes=[o for o in objects if o.type=='MESH'];assert len(meshes)==len(entry['meshes'])
    for obj in meshes:
        assert any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers),obj.name
        assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<.003 for v in obj.data.vertices),obj.name
        assert all(math.isfinite(x) for v in obj.data.vertices for x in v.co),obj.name
    guards=[o for o in meshes if o.name.startswith('FootGuards')];assert len(guards)==1
    guard=guards[0];assert len(guard.data.vertices)==12288 and guard.data.uv_layers.get('UVInstepPanel')
    images=set()
    for obj in meshes:
        for mat in obj.data.materials:
            if mat and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type=='TEX_IMAGE' and node.image:
                        assert node.image.size[0]>0,node.image.name;images.add(node.image.name)
    assert images
    report['checks'].append(dict(preset=kind,style=style,bones=len(rig.data.bones),meshes=len(meshes),guard_vertices=len(guard.data.vertices),readable_images=len(images),rig_parents_match=True,weights_normalized=True,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (OUT/'blender_validation.json').write_text(json.dumps(report,indent=2))
    if kind in ('Medium','Stocky','Female_Athletic') and style=='Standard':
        s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
        scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
        review.render(s,rig,scale,OUT/kind,'Export_Reimport',(3,-5,2),(0,0,1),2.6,700,850)
report['passed']=len(report['checks'])==18
report['scope']='Static full-character FBX roundtrip hierarchy, geometry, influences, UV and readable-texture checks. Representative renders; no cloth or animation roundtrip acceptance.'
(OUT/'blender_validation.json').write_text(json.dumps(report,indent=2))
