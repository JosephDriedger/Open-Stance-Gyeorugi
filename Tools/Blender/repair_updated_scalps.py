"""Preserve scalp silhouettes in existing reduced profiles; refresh exports."""
import bpy,sys,traceback,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as b
def run(kind,quick=False):
 d=b.OUT/kind;bpy.ops.wm.open_mainfile(filepath=str(d/'Preview.blend'))
 caps=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Hair_')]
 assert sum('Scalp_Coverage' in o.name for o in caps)==6
 references={}
 for o in caps:
  if 'Scalp_Coverage' in o.name:
   points=[o.matrix_world@v.co for v in o.data.shape_keys.key_blocks['Basis'].data]
   references[o.name]=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
 checks=[]
 bundle=d/'Scalp_Source.blend';bpy.data.libraries.write(str(bundle),set(caps),compress=True)
 levels={'Crowd_Near':800} if quick else {'Gameplay_High':2000,'Gameplay_Mid':1200,'Gameplay_Far':800,'Crowd_Near':800,'Crowd_Far':500}
 for level,budget in levels.items():
  path=d/(level+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_Body_'+kind]
  for o in list(bpy.data.objects):
   if o.type=='MESH' and o.name.startswith('Hair_'):bpy.data.objects.remove(o,do_unlink=True)
  old=set(bpy.data.objects)
  with bpy.data.libraries.load(str(bundle),link=False) as (a,z):z.objects=[n for n in a.objects if n.startswith('Hair_')]
  totals={}
  for o in z.objects:
   style=o.name.split('__')[0];totals[style]=totals.get(style,0)+b.suite.tris(o)
  for o in z.objects:
   bpy.context.scene.collection.objects.link(o);o.hide_set(False);b.suite.bind(o,rig)
   b.redirect(o,rig);b.redirect(o.data.shape_keys,rig)
   for mat in o.data.materials:
    if mat and mat.use_nodes:b.redirect(mat.node_tree,rig)
   # Reduction uses the unfitted basis; restore the selected helmet state after.
   wear=rig['Wear_Helmet'];rig['Wear_Helmet']=False;b.refresh(rig)
   style=o.name.split('__')[0];total_budget={'Gameplay_High':16000,'Gameplay_Mid':6500,'Gameplay_Far':2200,'Crowd_Near':1000,'Crowd_Far':350}[level]
   part_budget=max(30,round(total_budget*b.suite.tris(o)/totals[style]))
   if 'Scalp_Coverage' in o.name:part_budget=max(part_budget,budget)
   if 'Scalp_Coverage' in o.name:b.resample_scalp(o,bpy.data.objects['Head'],rig,level)
   else:b.reduce_mesh(o,part_budget)
   b.suite.weights(o,rig,2 if level.startswith('Crowd') else 4)
   rig['Wear_Helmet']=wear;b.refresh(rig)
  for o in list(bpy.data.objects):
   if o not in old and o not in z.objects and o.type=='ARMATURE':bpy.data.objects.remove(o,do_unlink=True)
  oldstyle=rig['HairStyle'];oldwear=rig['Wear_Helmet'];rig['Wear_Helmet']=False
  for index,style in enumerate(b.hair.STYLES):
   rig['HairStyle']=index;b.refresh(rig);o=bpy.data.objects['Hair_'+style+'__Scalp_Coverage'];e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());points=[e.matrix_world@v.co for v in e.data.vertices]
   bounds=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)];error=max(abs(a-v) for pair,ref in zip(bounds,references[o.name]) for a,v in zip(pair,ref))
   assert error<.018,(kind,level,style,error)
   checks.append({'profile':level,'hair':style,'max_bound_deviation_m':error,'passed':True})
  rig['HairStyle']=oldstyle;rig['Wear_Helmet']=oldwear;b.refresh(rig)
  counts={};deps=bpy.context.evaluated_depsgraph_get()
  for obj in b.meshes():
   if not obj.hide_render:
    e=obj.evaluated_get(deps);mesh=e.to_mesh();mesh.calc_loop_triangles();counts[obj.name]=len(mesh.loop_triangles);e.to_mesh_clear()
  report_path=d/(level+'_validation.json');report=json.loads(report_path.read_text());report['visible_evaluated_triangles']=counts;report['visible_evaluated_total']=sum(counts.values());report['hair_alignment_checked']=True
  report_path.write_text(json.dumps(report,indent=2))
  bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
 (d/'hair_alignment_validation.json').write_text(json.dumps({'passed':True,'checks':checks},indent=2))
 b.log(kind+' scalp repair complete')
 if not quick:
  import refresh_updated_exports as ex
  ex.run(kind)
  import check_updated_exports as check
  check.run(kind)
  import render_updated_previews as preview
  preview.render(kind)
 else:
  scene=bpy.context.scene;scene.render.filepath=str(d/'Scalp_Repair_Check.png');bpy.ops.render.render(write_still=True)
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:]
  for kind in [a for a in args if not a.startswith('--')]:run(kind,'--quick' in args)
 except:b.log(traceback.format_exc());raise
