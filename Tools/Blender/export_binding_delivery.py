"""Rebuild only affected sparring FBXs; keep crowd and unarmored assets intact."""
import bpy,sys,json,hashlib,time
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
ROOT=build.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/BindingDelivery'
old={x['file']:x['sha256'] for x in json.loads((ROOT/'Resources/Models/HairExportFinish/published.json').read_text())['files']}
batch=int(sys.argv[-1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for kind in build.PRESETS[batch::3]:
 rows=[]
 report=OUT/(kind+'_exports.json')
 if report.exists():continue
 for level in ['Gameplay_High','Gameplay_Mid','Gameplay_Far']:
  rel=Path('Resources/Models/CharacterSuite')/kind/(level+'.blend');native=OUT/'Files'/rel
  ready=OUT/(hashlib.sha256(rel.as_posix().encode()).hexdigest()[:16]+'.json');deadline=time.monotonic()+1800
  while not ready.exists():
   assert time.monotonic()<deadline,ready
   time.sleep(2)
  for style in [0,1]:
   bpy.ops.wm.open_mainfile(filepath=str(native));r=bpy.data.objects['RIG_Body_'+kind]
   r.animation_data.action=None
   for tr in r.animation_data.nla_tracks:tr.mute=True
   for p in r.pose.bones:p.matrix_basis=Matrix()
   r['JacketStyle']=style
   for key in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[key]=True
   build.refresh(r)
   relative=rel.parent/('WhiteVNeck' if style else '')/(level+'_Sparring.fbx');original=ROOT/relative
   assert sha(original)==old[relative.as_posix()]
   target=OUT/'Files'/relative;target.parent.mkdir(parents=True,exist_ok=True);build.export(r,target)
   bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(target));rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341
   meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert meshes
   assert any('Bound_Hem' in o.name for o in meshes)
   for o in meshes:
    assert any(m.type=='ARMATURE' and m.object==rigs[0] for m in o.modifiers),o.name
    assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<.003 for v in o.data.vertices),o.name
   rows.append({'file':relative.as_posix(),'before_sha256':old[relative.as_posix()],'sha256':sha(target),'reimport_passed':True,'bones':341,'normalized_weights':True})
 report.write_text(json.dumps({'files':rows},indent=2));print('BINDING_EXPORTS_VERIFIED',kind,flush=True)
