import bpy,sys,json,hashlib,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import repair_visual_fit as fix
import extend_garment_repairs as base
import build_single_helmet_study as view
OUT=fix.OUT/'Gear';OUT.mkdir(exist_ok=True)
try:
 bpy.ops.wm.open_mainfile(filepath=str(fix.ROOT/'Resources/Models/ProtectorReferenceV2/Chest_Protector_Library.blend'))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];signature=base.signature(r);actions=base.actions();count=0
 for o in s.objects:
  if o.type=='MESH' and o.name.startswith(('Quilted_Lace_Back__','Smooth_Buckle_Back__')):
   deltas=[]
   for v in o.data.vertices:
    q=o.matrix_world@v.co;deltas.append(Vector((0,.092*fix.smooth((1.23-q.z)/.27)*fix.smooth((-q.y-.07)/.10),0)))
   fix.shift(o,deltas);count+=1
 assert signature==base.signature(r) and actions==base.actions()
 s['ProtectorVisualFitRepair']='2026-10-16';p=OUT/'Chest_Protector_Library.blend';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(p),compress=True)
 s.cycles.samples=12;s.render.resolution_x=640;s.render.resolution_y=720;s.render.resolution_percentage=100
 for index,style in enumerate(['Quilted_Lace_Back','Smooth_Buckle_Back']):
  r['ProtectorDesign']=index;r['Wear_Protector']=True;r.update_tag();s.frame_set(2);s.frame_set(1)
  for name,pos in [('Front',(.7,-1.8,1.58)),('Rear',(.65,1.8,1.6)),('Side',(2,0,1.5))]:
   view.camera(s,pos,(0,0,1.27),.94);s.render.filepath=str(OUT/f'{style}_{name}.png');bpy.ops.render.render(write_still=True)
 (OUT/'validation.json').write_text(json.dumps({'passed':True,'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'parts':count,'rig_and_actions_unchanged':True},indent=2))
except:(OUT/'error.log').write_text(traceback.format_exc());raise
