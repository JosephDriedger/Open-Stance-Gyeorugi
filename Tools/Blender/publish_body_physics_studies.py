"""Publish reviewed experimental studies without replacing animation masters."""
import bpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
ROOT=base.ROOT
review=ROOT/'Resources/Models/FinalRefinement/BodyPhysics'
dest=ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies'
dest.mkdir(exist_ok=True)
baseline={x['file']:x['sha256'] for x in json.loads((review.parent/'HairRepeat/published.json').read_text())['files']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
for folder in sorted(review.iterdir()):
 if not (folder/'validation.json').exists():continue
 v=json.loads((folder/'validation.json').read_text());source=Path(v['source'])
 assert v['finite'] and v['frames']==144 and v['rig_preserved'] and v['rig_bones']==341
 assert sha(source)==baseline[source.relative_to(ROOT).as_posix()]
 kind=source.stem.removeprefix('OpenStance_').removesuffix('_Animation')
 bpy.ops.wm.open_mainfile(filepath=str(source));original=base.signature(bpy.data.objects['RIG_Body_'+kind]);actions=base.actions()
 staged=folder/('SecondaryCloth_'+folder.name+'_Wrap.blend')
 bpy.ops.wm.open_mainfile(filepath=str(staged));r=bpy.data.objects['RIG_Body_'+kind];s=bpy.context.scene
 assert base.signature(r)==original
 current=base.actions();assert all(current.get(k)==value for k,value in actions.items()),'Original actions changed'
 note='''EXPERIMENTAL BODY-TYPE CLOTH STUDY — 2026-10-23
Play sequentially from frame 1 through 144. Restart and clear caches after edits.
Body animation is a sample action; belt tails use actual Blender cloth.
Uniform vertices remain strongly pinned (0.96), so this is not fully free cloth.
Fitted pants collision proxy and post-cloth belt subdivision are enabled.
The 341-bone skeleton and original actions are preserved; the test action is added.
Front/side views at frames 1,26,35,72,144 reviewed. Belt crossing/twisting remains.
This does not establish collision-free motion for other clips or all gear combinations.
Physics is not a material setting or live Unreal cloth exported through FBX.
Canonical character masters are unchanged. Long-hair refinement remains unfinished.
'''
 t=bpy.data.texts.get('READ ME - Body Physics') or bpy.data.texts.new('READ ME - Body Physics');t.clear();t.write(note)
 s['ValidationStatus']='Experimental; sampled visual review completed; belt twisting and constrained uniform remain.'
 s.frame_set(1)
 bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.context.preferences.filepaths.save_version=0
 target=dest/staged.name
 bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(target));assert base.signature(bpy.data.objects['RIG_Body_'+kind])==original
 missing=[im.filepath for im in bpy.data.images if im.source=='FILE' and im.filepath and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists()]
 assert not missing,missing
 records.append({'file':str(target.relative_to(ROOT)),'sha256':sha(target),'source_sha256':sha(source),'frames':144,'rig_preserved':True,'original_actions_preserved':True,'external_images_resolve':True,'status':'experimental','visual_review':'Front and side at 1,26,35,72,144; twisting remains'})
 (review/'delivery.json').write_text(json.dumps({'files':records,'production_masters_changed':False},indent=2))
print('PUBLISHED_BODY_STUDIES',len(records),flush=True)
