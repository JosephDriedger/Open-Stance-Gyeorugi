import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
from refine_pants_cloth import configure
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/PantsClothDeliveryV3';OUT.mkdir(exist_ok=True)
kinds=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
for kind in kinds:
 folder=OUT/kind;folder.mkdir(exist_ok=True)
 if (folder/'validation.json').exists():continue
 source=ROOT/f'Resources/Models/Animation/Physics/Body_Type_Studies/SecondaryCloth_{kind}_Wrap.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];r['BlenderCloth']=False;s.frame_set(1);bpy.context.view_layer.update()
 assert configure(s)
 for o in s.objects:
  if o.type!='MESH' or o.name=='Pants':continue
  for m in o.modifiers:
   if m.type=='CLOTH':
    for prop in ('show_viewport','show_render'):m.driver_remove(prop);setattr(m,prop,False)
 r['BlenderCloth']=True;r['Wear_Protector']=False;r['Wear_Helmet']=False;r.update_tag();s.frame_set(1)
 pants=bpy.data.objects['Pants'];cloth=next(m for m in pants.modifiers if m.type=='CLOTH');cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=144
 s.frame_end=144;s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 for frame in range(1,145):
  s.frame_set(frame);ev=pants.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
  assert all(math.isfinite(x) and abs(x)<5 for v in mesh.vertices for x in pants.matrix_world@v.co),(kind,frame)
  ev.to_mesh_clear()
  if frame in (26,35,144):review.render(s,r,scale,folder,'Side_'+str(frame),(4,-.8,1.65),(0,-.25,.95),2.25,480,540)
 (folder/'validation.json').write_text(json.dumps({'passed':True,'kind':kind,'frames':144,'scope':'Pants-only physics; other cloth disabled to isolate this change. Visual review required.'},indent=2))
 print('PANTS_CLOTH_VALIDATED',kind,flush=True)


