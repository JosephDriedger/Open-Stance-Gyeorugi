"""Reference-informed fitted chest protectors; background Blender only."""
import bpy, math, json, sys, traceback
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as base
import rebuild_reference_helmets as u
import build_character_suite as suite
OUT=base.ROOT/'Resources/Models/ProtectorStudy';OUT.mkdir(exist_ok=True)
REFERENCE='https://www.daedo.com/products/pro-16533'

def plain(name,color,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough
 return m

def surface(a,t,offset=0,quilt=False):
 # Anatomical taper, rib clearance and a lifted side hem above the hips.
 low=1.020+.048*math.sin(a)**2+.012*max(0,-math.cos(a))
 high=1.395-.077*math.sin(a)**2-.035*max(0,-math.cos(a))-.020*math.exp(-(a/.22)**2)
 z=low+(high-low)*t
 rx=base.interpolate(z,[(1.02,.207),(1.12,.216),(1.25,.230),(1.40,.220)])
 ry=base.interpolate(z,[(1.02,.183),(1.12,.189),(1.25,.195),(1.40,.181)])
 # Shallow compression channels are geometry, not decorative floating cords.
 groove=sum(.0018*math.exp(-((t-q)/.018)**2) for q in [.22,.44,.66,.84]) if quilt else 0
 return Vector(((rx+offset-groove)*math.sin(a),-.006-(ry+offset-groove)*math.cos(a),z))

def shell(mat,quilt):
 n=128;rows=40;verts=[];faces=[]
 for j in range(rows+1):
  for i in range(n+1):verts.append(surface(-2.68+5.36*i/n,j/rows,quilt=quilt))
 for j in range(rows):
  for i in range(n):k=j*(n+1)+i;faces.append((k,k+1,k+n+2,k+n+1))
 o=base.smooth_surface(u.mesh('Padded_Torso_Shell',verts,faces,mat),.022,1)
 return o

def band(name,points,width,mat):
 vs=[];fs=[]
 for p in points:vs.extend([(p[0]-width/2,p[1],p[2]),(p[0]+width/2,p[1],p[2])])
 for i in range(len(points)-1):fs.append((2*i,2*i+1,2*i+3,2*i+2))
 return base.smooth_surface(u.mesh(name,vs,fs,mat),.008,2)

def build(rig,style):
 foam=u.material('Protector_'+style+'_Synthetic_Leather',rig,.43)
 white=plain('Protector_Ivory_Binding',(.76,.75,.70),.68)
 thread=plain('Protector_Seam_Thread',(.48,.47,.43),.8)
 dark=plain('Protector_Buckle',(.023,.025,.028),.53)
 quilt=style=='Quilted_Lace_Back';parts=[shell(foam,quilt)]
 jacket=bpy.data.objects['Jacket'];evaluated=jacket.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
 garment=BVHTree.FromPolygons([jacket.matrix_world@v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons]);evaluated.to_mesh_clear()
 for t in [0,1]:
  pts=[surface(-2.68+5.36*i/160,t,.010,quilt) for i in range(161)]
  parts.append(u.tube('Bound_'+('Hem' if t==0 else 'Upper_Edge'),pts,.005,white))
 for a in [-2.68,2.68]:
  parts.append(u.tube('Rear_Wing_Binding',[surface(a,i/60,.010,quilt) for i in range(61)],.005,white))
 # Separate white shoulder straps connect upper chest to rear wings.
 for s in [-1,1]:
  pts=[]
  for i in range(65):
   t=i/64;x=s*(.102+.008*math.sin(math.pi*t));y=-.157+.307*t;z=1.350-.028*t+.155*math.sin(math.pi*t)
   if z<1.455:
    front=t<.5;hit=garment.ray_cast(Vector((x,-1 if front else 1,z)),Vector((0,1 if front else -1,0)))[0]
    if hit:y=min(y,hit.y-.008) if front else max(y,hit.y+.008)
   pts.append((x,y,z))
  parts.append(band('Padded_Shoulder_Strap',pts,.054,white))
  for edge in [-1,1]:
   parts.append(u.tube('Shoulder_Seam',[(p[0]+edge*.022,p[1],p[2]+.0046) for p in pts],.0007,thread))
 # Edge stitching follows the shell, with visible individual stitches.
 for t in [.028,.972]:
  for i in range(108):
   a=-2.63+5.26*i/108
   parts.append(u.tube('Binding_Stitch',[surface(a,t,.0125,quilt),surface(a+.025,t,.0125,quilt)],.00055,thread))
 # Keep stitch meshes grouped as a single editable object.
 stitches=[o for o in parts if o.name.startswith('Binding_Stitch')]
 u.activate(stitches[0])
 for o in stitches:o.select_set(True)
 bpy.ops.object.join();stitches[0].name='Edge_Stitching';parts=[o for o in parts if o not in stitches]+[stitches[0]]
 if quilt:
  anchors=[]
  for t in [.15,.38,.61,.82]:
   pair=[]
   for s in [-1,1]:
    p=surface(s*2.68,t,.014,quilt);pair.append(p)
    ring=[(p.x+.008*math.cos(math.tau*i/32),p.y+.006,p.z+.011*math.sin(math.tau*i/32)) for i in range(33)]
    parts.append(u.tube('Reinforced_Lace_Loop',ring,.0025,white))
   anchors.append(pair)
  for k in range(len(anchors)-1):
   for side in [0,1]:
    a=anchors[k][side];b=anchors[k+1][1-side]
    pts=[(a.x+(b.x-a.x)*i/20,max(a.y,b.y)+.015+.008*math.sin(math.pi*i/20),a.z+(b.z-a.z)*i/20) for i in range(21)]
    parts.append(u.tube('Crossed_Back_Lacing',pts,.003,white))
 else:
  for t in [.24,.63]:
   a=surface(-2.68,t,.018);b=surface(2.68,t,.018)
   pts=[(a.x+(b.x-a.x)*i/32,max(a.y,b.y)+.018,a.z) for i in range(33)]
   # Rear straps span horizontally; width lies along the vertical torso axis.
   vs=[]
   for p in pts:vs.extend([(p[0],p[1],p[2]-.018),(p[0],p[1],p[2]+.018)])
   o=u.mesh('Rear_Adjustment_Webbing',vs,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(32)],white)
   m=o.modifiers.new('Strap thickness','SOLIDIFY');m.thickness=.004;u.apply(o,m);u.bevel(o,.001,2);parts.append(o)
   y=max(a.y,b.y)+.024;z=a.z
   pts=[(-.024,y,z-.022),(.024,y,z-.022),(.024,y,z+.022),(-.024,y,z+.022),(-.024,y,z-.022)]
   parts.append(u.tube('Rear_Adjustment_Buckle',pts,.004,dark))
 return parts

def skin(o,rig):
 o.vertex_groups.clear()
 anchors=[('spine_02',1.02),('spine_03',1.12),('spine_04',1.23),('spine_05',1.37)]
 groups={n:o.vertex_groups.new(name=n) for n,z in anchors}
 for v in o.data.vertices:
  z=v.co.z
  if z<=anchors[0][1]:groups[anchors[0][0]].add([v.index],1,'REPLACE')
  elif z>=anchors[-1][1]:groups[anchors[-1][0]].add([v.index],1,'REPLACE')
  else:
   for (a,za),(b,zb) in zip(anchors,anchors[1:]):
    if za<=z<zb:
     w=(z-za)/(zb-za);groups[a].add([v.index],1-w,'REPLACE');groups[b].add([v.index],w,'REPLACE');break
 suite.bind(o,rig)

def run():
 bpy.ops.wm.open_mainfile(filepath=str(base.ROOT/'Resources/Models/HelmetVariants/Helmet_Design_Library.blend'))
 rig=bpy.data.objects['RIG_Body_Medium'];scene=bpy.context.scene
 for o in list(bpy.data.objects):
  if o.type=='MESH' and o.name.startswith('Protector'):bpy.data.objects.remove(o,do_unlink=True)
 rig['ProtectorDesign']=0;rig.id_properties_ui('ProtectorDesign').update(min=0,max=1,description='0 Quilted Lace Back; 1 Smooth Buckle Back')
 rig['Wear_Protector']=True;rig['MatchSide']=0
 names=['Quilted_Lace_Back','Smooth_Buckle_Back'];allparts=[]
 for index,name in enumerate(names):
  parts=build(rig,name);allparts+=parts;coll=bpy.data.collections.new('Protector_'+name);scene.collection.children.link(coll)
  for o in parts:
   for c in list(o.users_collection):c.objects.unlink(o)
   coll.objects.link(o);o.name=name+'__'+o.name;skin(o,rig);o['ReferenceURL']=REFERENCE
   for attr in ['hide_render','hide_viewport']:
    suite.driver(o,attr,rig,'ProtectorDesign',f'x != {index}');d=o.animation_data.drivers.find(attr).driver;v=d.variables.new();v.name='wear';v.targets[0].id=rig;v.targets[0].data_path='["Wear_Protector"]';d.expression=f'(x != {index}) or not wear'
 scene.render.resolution_x=1100;scene.render.resolution_y=1100
 base.camera(scene,(.70,-1.8,1.58),(0,0,1.27),.94);rig.update_tag();scene.frame_set(2);scene.frame_set(1)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Chest_Protector_Library.blend'),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Chest_Protector_Library.blend'))
 rig=bpy.data.objects['RIG_Body_Medium'];scene=bpy.context.scene
 for index,name in enumerate(names):
  rig['ProtectorDesign']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
  for view,pos in [('Front',(.7,-1.8,1.58)),('Rear',(.65,1.8,1.6))]:
   base.camera(scene,pos,(0,0,1.27),.94);scene.render.filepath=str(OUT/(name+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
 # Validate the saved deliverable rather than just the construction scene.
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Chest_Protector_Library.blend'))
 scene=bpy.context.scene;rig=bpy.data.objects['RIG_Body_Medium'];report={'reference':REFERENCE,'scope':'Medium body preview; other body fits and gameplay exports pending','styles':{}}
 for index,name in enumerate(names):
  rig['ProtectorDesign']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
  objects=list(bpy.data.collections['Protector_'+name].objects);assert all(not o.hide_render for o in objects)
  count=0
  for o in objects:
   assert all(abs(sum(g.weight for g in v.groups)-1)<1e-5 and 1<=len(v.groups)<=2 for v in o.data.vertices)
   o.data.calc_loop_triangles();count+=len(o.data.loop_triangles)
  deps=bpy.context.evaluated_depsgraph_get();o=objects[0];before=(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co).copy()
  bone=rig.pose.bones['spine_03'];bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((0,0,1),.15);bpy.context.view_layer.update()
  delta=(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co-before).length;assert delta>.001
  bone.rotation_quaternion=Quaternion();bpy.context.view_layer.update()
  report['styles'][name]={'parts':len(objects),'triangles':count,'normalized_weights':True,'torso_pose_displacement_m':delta}
 rig['Wear_Protector']=False;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
 assert all(o.hide_render for n in names for o in bpy.data.collections['Protector_'+n].objects)
 report['saved_file_reopened']=True;report['gear_toggle_passed']=True
 (OUT/'validation.json').write_text(json.dumps(report,indent=2));(OUT/'build.log').write_text('COMPLETE')

if __name__=='__main__':
 try:run()
 except:(OUT/'build.log').write_text(traceback.format_exc());raise
