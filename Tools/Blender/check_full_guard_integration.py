import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;production_root='--production-root' in sys.argv
OUT=ROOT/'Resources/Models/FinalRefinement'/('StockyProductionRoot' if production_root else 'StockyGuardIntegration');rows=[]
for label,guardname in (('Standard','FootGuards'),('Padded','FootGuards_PaddedInstep')):
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardLocalROMSmooth/Candidate.blend'))
 for o in list(bpy.context.scene.objects):
  if o.type=='ARMATURE' or (o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)):bpy.data.objects.remove(o,do_unlink=True)
 before=set(bpy.context.scene.objects)
 bpy.ops.import_scene.fbx(filepath=str(OUT/f'Stocky_Sparring_{label}.fbx'),use_anim=False)
 imported=[o for o in bpy.context.scene.objects if o not in before];rigs=[o for o in imported if o.type=='ARMATURE'];assert len(rigs)==1
 r=rigs[0];assert len(r.data.bones)==341
 meshes=[o for o in imported if o.type=='MESH'];assert len(meshes)>20
 for o in meshes:
  assert any(m.type=='ARMATURE' and m.object==r for m in o.modifiers),o.name
  assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<.003 for v in o.data.vertices),o.name
  assert all(math.isfinite(x) for v in o.data.vertices for x in v.co),o.name
 guards=[o for o in meshes if o.name.startswith('FootGuards')];assert len(guards)==1
 guard=guards[0];assert guard.name.split('.')[0]==guardname
 assert len(guard.data.vertices)==12288 and guard.data.uv_layers.get('UVInstepPanel')
 missing=[];images=set()
 for o in meshes:
  for mat in o.data.materials:
   if mat and mat.use_nodes:
    for n in mat.node_tree.nodes:
     if n.type=='TEX_IMAGE' and n.image:
      images.add(n.image.name)
      if n.image.size[0]==0:missing.append(n.image.name)
 assert not missing,missing
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 review.render(s,r,scale,OUT,label+'_Full_Reimport',(3,-5,2),(0,0,1),2.6,750,850)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{label}_Reimport.blend'),compress=True)
 rows.append({'style':label,'meshes':len(meshes),'bones':341,'guard':guard.name,'guard_vertices':12288,'readable_images':len(images),'normalized_four_influence_weights':True})
(OUT/'blender_validation.json').write_text(json.dumps({'passed':True,'production_installed':False,'scope':'Full rest-character reimport structure, textures and rendered review. No animation/collision acceptance.','checks':rows},indent=2))
