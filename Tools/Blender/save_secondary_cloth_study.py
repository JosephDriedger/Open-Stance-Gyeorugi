import bpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from refine_final_hair import seam
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'Resources/Models/FinalRefinement/ClothSettle_0/Pilot.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];seam(s)
assert len(r.data.bones)==341
for o in s.objects:
 if o.name.startswith('SIM_Capsule_'):
  d=o.driver_add('hide_viewport').driver;v=d.variables.new();v.name='enabled';v.targets[0].id=r;v.targets[0].data_path='["BlenderCloth"]';d.expression='not enabled'
s['ValidationStatus']='Experimental: constrained uniform cloth and free belt tails. Belt folding still needs refinement.'
text=bpy.data.texts.get('READ ME - Secondary Cloth') or bpy.data.texts.new('READ ME - Secondary Cloth')
text.clear();text.write('''SECONDARY CLOTH STUDY - 2026-10-23
Experimental, not the production character master.
Play sequentially from frame 1. Frames 1-72 contain the front kick; 73-144 allow settling.
The BlenderCloth property on RIG_Body_Medium enables actual Blender cloth simulation.
Uniform cloth uses strong pinning (0.96 away from anchors) to retain the authored garment shape.
Belt tails are free below their attachment. The sharper folds still need refinement.
Detailed body contacts caused dents; uniform uses simplified limb contacts in this study.
Belt contacts use garment proxies with old clip-baked shape animation cleared.
Clear/free caches and restart at frame 1 after wardrobe, animation or physics changes.
The simulation is not exported as live FBX/Unreal physics. Bake separately for fixed playback,
or author runtime cloth in the game engine. This scene does not establish collision-free motion.
''')
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
dest=ROOT/'Resources/Models/Animation/Physics/SecondaryCloth_Kick_Study.blend'
assert not dest.exists(),'Refuse to overwrite an existing study'
bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(dest));assert bpy.context.scene.get('ValidationStatus')
report={'file':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'status':'experimental','frame_range':[1,144],'rig_bones':341}
(ROOT/'Resources/Models/FinalRefinement/secondary_cloth_study.json').write_text(json.dumps(report,indent=2))
