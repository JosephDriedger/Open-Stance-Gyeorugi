import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
ROOT=a.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyCuffFit';OUT.mkdir(exist_ok=True)
for mm in (3,6):
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_Stocky_Wrap.blend'))
 s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];r['BlenderCloth']=False;r['Wear_Protector']=False;r['Wear_Helmet']=False;r.update_tag();s.frame_set(1);bpy.context.view_layer.update()
 o=bpy.data.objects['Pants'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;points=[o.matrix_world@v.co for v in o.data.vertices];bottom=min(p.z for p in points);inv=o.matrix_world.inverted().to_3x3();deltas=[]
 axes={side:(r.matrix_world@r.data.bones['calf_'+side].head_local,r.matrix_world@r.data.bones['foot_'+side].head_local) for side in 'lr'}
 for p in points:
  aa,bb=min(axes.values(),key=lambda pair:abs(p.x-pair[1].x));t=(p.z-aa.z)/(bb.z-aa.z);center=aa+(bb-aa)*t;direction=p-center;direction.z=0
  f=max(0,min(1,(bottom+.08*scale-p.z)/(.065*scale)));f=f*f*(3-2*f)
  delta=inv@(direction.normalized()*f*mm*.001*scale) if direction.length>.01 else Vector()
  deltas.append(delta)
 keys=o.data.shape_keys
 if keys:
  for key in keys.key_blocks:
   for v,d in zip(key.data,deltas):v.co+=d
  for v,k in zip(o.data.vertices,keys.key_blocks[0].data):v.co=k.co
 else:
  for v,d in zip(o.data.vertices,deltas):v.co+=d
 s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True;s.frame_set(35)
 a.render(s,r,scale,OUT,f'Cuff_{mm}mm',(3,-.8,1.65),(0,-.25,.95),2.25,720,810)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'Candidate_{mm}mm.blend'),compress=True)
 print('CUFF_TRIAL',mm,flush=True)
