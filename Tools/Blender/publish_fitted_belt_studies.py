"""Deliver the reviewed Medium physics studies, without changing character masters."""
import bpy,sys,json,hashlib,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
ROOT=base.ROOT;S=ROOT/'Resources/Models/FinalRefinement';destdir=ROOT/'Resources/Models/Animation/Physics'
old=json.loads((S/'secondary_cloth_study.json').read_text());original=ROOT/old['file']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(original)==old['sha256'],'Study changed since its last recorded revision'
archive=ROOT/'Resources/Models/Archive/Before_Fitted_Belt_Contact_20261023';archive.mkdir(exist_ok=True)
backup=archive/original.name;assert not backup.exists();shutil.copy2(original,backup);assert sha(backup)==old['sha256']
bpy.ops.wm.open_mainfile(filepath=str(original));rig=base.signature(bpy.data.objects['RIG_Body_Medium']);actions=base.actions()
records=[]
for suffix in ['', '_VNeck']:
 source=S/('BeltFittedContact'+suffix);validation=json.loads((source/'validation.json').read_text());assert validation['finite'] and validation['frames']==144
 bpy.ops.wm.open_mainfile(filepath=str(source/'Belt_Surface_Study.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium']
 assert base.signature(r)==rig and base.actions()==actions
 for name in ['Belt_Tail_Left','Belt_Tail_Right']:
  sub=bpy.data.objects[name].modifiers['Smooth woven belt surface']
  for prop in ['show_viewport','show_render']:
   d=sub.driver_add(prop).driver;v=d.variables.new();v.name='live';v.targets[0].id=r;v.targets[0].data_path='["BlenderCloth"]';d.expression='live'
 s['ValidationStatus']='Experimental: fitted single belt contact surface. Medium wrap and V-neck kick/settling reviewed; other body types and moves unvalidated.'
 text=bpy.data.texts['READ ME - Secondary Cloth'];text.clear();text.write('''FITTED BELT CONTACT STUDY - 2026-10-23
Experimental Medium character study. Play sequentially from frame 1.
Frames 1-72: kick. Frames 73-144: settling. Toggle BlenderCloth on the body rig.
Actual Blender cloth drives the belt tails; there are no belt motion keyframes.
The belt uses one offset pants contact proxy instead of overlapping body/jacket contacts.
Offset varies from 5 to 18 mm at Medium scale. Zero contact friction allows sliding.
Post-simulation subdivision smooths the visible belt while retaining the solver mesh.
Both uniform styles were reviewed over this 144-frame test. Some twisting remains.
This is not an all-body, all-animation collision guarantee. Full free uniform cloth remains unfinished.
Clear caches and restart at frame 1 after changing the animation, wardrobe or settings.
Physics does not transfer as live Unreal cloth through FBX. Bake fixed playback separately.
''')
 s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;staged=source/'Reviewed_Study.blend'
 bpy.ops.wm.save_as_mainfile(filepath=str(staged),compress=True);bpy.ops.wm.open_mainfile(filepath=str(staged))
 assert base.signature(bpy.data.objects['RIG_Body_Medium'])==rig and base.actions()==actions
 target=destdir/('SecondaryCloth_Kick_Study'+suffix+'.blend')
 if suffix:assert not target.exists()
 else:assert sha(target)==old['sha256']
 shutil.copy2(staged,target);assert sha(target)==sha(staged)
 records.append({'file':str(target.relative_to(ROOT)),'sha256':sha(target),'status':'experimental','frame_range':[1,144],'rig_bones':341,'body_rig_and_actions_preserved':True})
(S/'fitted_belt_delivery.json').write_text(json.dumps({'files':records,'archive':str(archive),'scope':'Medium physics studies only; no character master or FBX changed'},indent=2))
(S/'secondary_cloth_study.json').write_text(json.dumps(records[0],indent=2))
print('FITTED_BELT_STUDIES_DELIVERED',flush=True)
