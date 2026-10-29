import bpy,sys,json,hashlib,traceback
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/UniformRebuild')
def log(s):
 with (OUT/'finish.log').open('a') as f:f.write(str(s)+'\n')
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Uniform_Corrected.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];names=json.loads((OUT/'cloth_objects.json').read_text())
 # Fit the pinned seam inside the belt, with a gradual transition below it.
 for name in names:
  if not name.startswith('Jacket'):continue
  o=bpy.data.objects[name]
  weights=[max(0,min(1,(v.co.z-.865)/.10)) for v in o.data.vertices]
  for key in o.data.shape_keys.key_blocks:
   for v,t in zip(key.data,weights):v.co.x*=1-.075*t;v.co.y=-.012+(v.co.y+.012)*(1-.04*t)
  for v,p in zip(o.data.vertices,o.data.shape_keys.key_blocks[0].data):v.co=p.co
 # Resolve any small residual contact against the actual visible trouser surface.
 pants=bpy.data.objects['Pants'];solid=[m for m in pants.modifiers if m.type=='SOLIDIFY']
 for m in solid:m.show_viewport=False
 report={'contact_corrections':{},'body_bones':len(r.data.bones)}
 for f in range(1,73):
  scene.frame_set(f);bpy.context.view_layer.update();ev=pants.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
  tree=BVHTree.FromPolygons([pants.matrix_world@v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons]);ev.to_mesh_clear()
  transform=r.matrix_world@r.pose.bones['pelvis'].matrix@r.data.bones['pelvis'].matrix_local.inverted()@r.matrix_world.inverted();inverse=transform.inverted()
  for name in names:
   o=bpy.data.objects[name];key=o.data.shape_keys.key_blocks[f'ClothBake_{f:02d}'];count=0;maximum=0
   for v in key.data:
    p=transform@v.co;hit,normal,_,distance=tree.find_nearest(p)
    if hit is not None and distance<.035 and (p-hit).dot(normal)<.004 and p.z<1.16:
     target=hit+normal*.006;amount=(target-p).length
     v.co=inverse@target;count+=1;maximum=max(maximum,amount)
   row=report['contact_corrections'].setdefault(name,{'vertices_over_all_frames':0,'maximum_m':0})
   row['vertices_over_all_frames']+=count;row['maximum_m']=max(row['maximum_m'],maximum)
 for m in solid:m.show_viewport=True
 scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Uniform_Corrected.blend'))
 for f in [1,26,35,72]:
  scene.frame_set(f);scene.render.filepath=str(OUT/f'Final_Side_{f}.png');bpy.ops.render.render(write_still=True)
 build.view.camera(scene,(.8,-4,1.75),(0,-.12,.94),2.3)
 for f in [1,26,35,72]:
  scene.frame_set(f);scene.render.filepath=str(OUT/f'Final_Front_{f}.png');bpy.ops.render.render(write_still=True)
 build.view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
 scene.frame_set(1);build.export(r,OUT/'Front_Kick_Corrected.fbx',True)
 report['fbx_sha256']=hashlib.sha256((OUT/'Front_Kick_Corrected.fbx').read_bytes()).hexdigest()
 (OUT/'contact_report.json').write_text(json.dumps(report,indent=2));log('REVIEW AND EXPORT READY')
except:log(traceback.format_exc());raise
