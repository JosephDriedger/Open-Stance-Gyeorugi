"""Test a smoother render surface over the existing physical belt mesh."""
import bpy,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
root=a.ROOT;out=root/'Resources/Models/FinalRefinement/BeltSurface';out.mkdir(exist_ok=True)
style=int(sys.argv[-1]) if '--' in sys.argv else 0
if style:out=out.with_name(out.name+'_VNeck');out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/Animation/Physics/SecondaryCloth_Kick_Study.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];changes=[]
if style:
 r['BlenderCloth']=False;r['JacketStyle']=style;r.update_tag();s.frame_set(2);s.frame_set(1);r['BlenderCloth']=True;r.update_tag();bpy.context.view_layer.update()
for name in ['Belt_Tail_Left','Belt_Tail_Right']:
 o=bpy.data.objects[name];before=sum(p.use_smooth for p in o.data.polygons)
 for p in o.data.polygons:p.use_smooth=True
 sub=o.modifiers.new('Smooth woven belt surface','SUBSURF');sub.subdivision_type='CATMULL_CLARK';sub.levels=2;sub.render_levels=2
 bpy.context.view_layer.objects.active=o
 solid=next((i for i,m in enumerate(o.modifiers) if m.type=='SOLIDIFY'),len(o.modifiers)-1)
 bpy.ops.object.modifier_move_to_index(modifier=sub.name,index=solid)
 changes.append({'object':name,'previous_smooth_faces':before,'faces':len(o.data.polygons),'subdivision_after_simulation':True})
s.cycles.samples=16;s.frame_set(1)
for frame in range(1,145):
 s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
 for name in ['Belt_Tail_Left','Belt_Tail_Right']:
  o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh()
  assert all(math.isfinite(x) and abs(x)<5 for v in me.vertices for x in o.matrix_world@v.co)
  ev.to_mesh_clear()
 if frame in [1,26,35,72,144]:
  a.render(s,r,1,out,'Front_'+str(frame),(.2,-4,1.3),(0,0,.96),1.25,640,720)
  a.render(s,r,1,out,'Side_'+str(frame),(4,-.8,1.65),(0,-.3,.95),2.25,640,720)
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'Belt_Surface_Study.blend'),compress=True)
(out/'validation.json').write_text(json.dumps({'frames':144,'finite':True,'changes':changes,'production_installed':False},indent=2))
print('BELT_SURFACE_COMPLETE',flush=True)
