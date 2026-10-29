import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import rebuild_updated_characters as build
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/BeltFit');bpy.ops.wm.open_mainfile(filepath=str(out/'Medium_Sparring_Samples.blend'));s=bpy.context.scene;s.frame_set(1)
report=[]
for o in s.objects:
 if o.type=='MESH' and not o.hide_render:
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();ps=[o.matrix_world@v.co for v in m.vertices];report.append({'name':o.name,'n':len(ps),'z':[min(p.z for p in ps),max(p.z for p in ps)],'mods':[(x.name,x.type) for x in o.modifiers]});ev.to_mesh_clear()
(out/'objects.json').write_text(json.dumps(report,indent=2))
build.view.camera(s,(3,-1,1.55),(0,-.02,1.01),.83)
for name in ['Pants','Jacket_Back','Jacket_Front_Left','Jacket_Front_Right']:
 bpy.data.objects[name].hide_render=True
 s.render.filepath=str(out/('Hide_'+name+'.png'));bpy.ops.render.render(write_still=True)
