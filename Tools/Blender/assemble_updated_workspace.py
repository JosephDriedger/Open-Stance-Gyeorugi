"""Assemble all nine updated animation scenes in staging, without replacing masters."""
import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as b
try:
 bpy.ops.wm.read_factory_settings(use_empty=True);default=bpy.context.scene;rows=[]
 for kind in b.PRESETS:
  source=b.OUT/kind/f'OpenStance_{kind}_Animation.blend'
  with bpy.data.libraries.load(str(source),link=False) as (a,z):z.scenes=['Fighter_'+kind]
  scene=z.scenes[0];assert scene is not None
  for c in scene.collection.children:c.name=kind+'_'+c.name
  for o in scene.objects:
   if not o.name.startswith('RIG_'):o.name=kind+'_'+o.name.split('.')[0]
  rows.append({'preset':kind,'scene':scene.name})
 bpy.context.window.scene=bpy.data.scenes['Fighter_Medium'];bpy.data.scenes.remove(default)
 text=bpy.data.texts.get('UPDATED_START_HERE.txt') or bpy.data.texts.new('UPDATED_START_HERE.txt')
 text.write('Updated character workspace: nine Fighter scenes. Select RIG_Body_<preset> for wardrobe, hair, eyebrow and gear selectors and body animation. RIG_Face_<preset> supports facial bone animation. Marker guides are not calibrated capture data. See Models and Rigs/START HERE.md and Resources/Models/Animation/README.md. Save animation work as a new file.\n')
 path=b.OUT/'OpenStance_Characters_Workspace.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(path))
 for row in rows:
  kind=row['preset'];scene=bpy.data.scenes[row['scene']];bpy.context.window.scene=scene
  rig=next(o for o in scene.objects if o.name=='RIG_Body_'+kind);face=next(o for o in scene.objects if o.name=='RIG_Face_'+kind)
  assert len(rig.data.bones)==341 and len(face.data.bones)==874
  guides=[o for o in scene.objects if o.get('MarkerLabel')];assert len(guides)==41 and all(o.parent==rig for o in guides)
  assert all(c.target==rig for bone in face.pose.bones for c in bone.constraints if c.type=='COPY_TRANSFORMS')
  row.update(body_bones=341,face_bones=874,marker_guides=41,saved_file_reopened=True)
 (b.OUT/'workspace_validation.json').write_text(json.dumps({'passed':True,'scenes':rows},indent=2));b.log('Combined workspace complete')
except:b.log(traceback.format_exc());raise
