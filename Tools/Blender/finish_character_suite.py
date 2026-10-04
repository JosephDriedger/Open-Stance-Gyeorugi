"""Finalize coverage, crowd motion, team materials, and explicit runtime exports."""
import bpy,math,json,sys,traceback
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/CharacterSuite'
sys.path.insert(0,str(Path(__file__).parent))
import build_character_suite as suite
def update():bpy.context.view_layer.update()
def solve_arm(rig,side,target,pole):
 update();u=rig.pose.bones['upperarm_'+side];l=rig.pose.bones['lowerarm_'+side];h=rig.pose.bones['hand_'+side]
 a=u.matrix.translation.copy();b=l.matrix.translation.copy();c=h.matrix.translation.copy()
 target=rig.matrix_world.inverted()@Vector(target);pole=rig.matrix_world.inverted()@Vector(pole)
 l1=(b-a).length;l2=(c-b).length;axis=(target-a).normalized();distance=min((target-a).length,(l1+l2)*.98)
 target=a+axis*distance;d=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-d*d))
 perp=pole-a-axis*(pole-a).dot(axis);perp.normalize();elbow=a+axis*d+perp*height
 q=(b-a).rotation_difference(elbow-a);u.matrix=Matrix.Translation(a)@q.to_matrix().to_4x4()@Matrix.Translation(-a)@u.matrix
 update();b=l.matrix.translation.copy();c=h.matrix.translation.copy();q=(c-b).rotation_difference(target-b)
 l.matrix=Matrix.Translation(b)@q.to_matrix().to_4x4()@Matrix.Translation(-b)@l.matrix;update()
def actions(rig):
 rig.animation_data.action=None
 for tr in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(tr)
 for a in list(bpy.data.actions):
  if a.name.startswith('Crowd_'):bpy.data.actions.remove(a)
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 results=[]
 for label in ['StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave']:
  rig.animation_data.action=None
  for frame in range(1,62,3):
   t=(frame-1)*math.tau/60
   for p in rig.pose.bones:p.matrix_basis=Matrix();p.rotation_mode='QUATERNION'
   def rotate(n,axis,angle):
    p=rig.pose.bones[n];p.rotation_quaternion=Quaternion(p.bone.matrix_local.to_quaternion().inverted()@Vector(axis),angle)
   seated=label.startswith('Seated');drop=.43*scale if seated else 0
   if seated:
    p=rig.pose.bones['pelvis'];p.location=p.bone.matrix_local.to_3x3().inverted()@rig.matrix_world.to_3x3().inverted()@Vector((0,0,-drop))
    for s in 'lr':rotate('thigh_'+s,(1,0,0),-math.pi/2);rotate('calf_'+s,(1,0,0),math.pi/2)
   rotate('spine_03',(0,1,0),.012*math.sin(t));update()
   for side,sign in [('l',1),('r',-1)]:
    target=(sign*.29,-.055,.80)
    if label=='SeatedIdle':target=(sign*.24,-.36,.62/scale)
    if label=='SeatedClap':target=(sign*(.046+.065*(1-math.cos(t*2))),-.36,1.22-drop/scale)
    if label=='Cheer':target=(sign*.39,-.04,1.83+.035*math.sin(t))
    if label=='Wave' and side=='r':target=(-.42-.04*math.sin(2*t),-.10,1.69)
    target=tuple(x*scale for x in target);pole=(sign*.7*scale,-.15*scale,(1.05*scale-drop))
    solve_arm(rig,side,target,pole)
   for p in rig.pose.bones:
    p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name);p.keyframe_insert('location',frame=frame,group=p.name)
  a=rig.animation_data.action;a.name='Crowd_'+label;a.use_fake_user=True;results.append(a.name)
 rig.animation_data.action=None
 for p in rig.pose.bones:p.matrix_basis=Matrix()
 bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=61;bpy.context.scene.render.fps=30
 return results
def team_material(rig,meshes):
 if bpy.data.materials.get('M_Match_Team'):return
 rig['MatchSide']=0;rig.id_properties_ui('MatchSide').update(min=0,max=1,description='0 Chung blue; 1 Hong red. Assign from match rules.')
 material=None
 for o in meshes:
  if not o.name.startswith(('Helmet','Protector','Gloves','FootGuards')) or not o.data.uv_layers:continue
  if material is None:
   material=o.data.materials[0].copy();material.name='M_Match_Team';bs=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');socket=bs.inputs['Base Color']
   for link in list(socket.links):material.node_tree.links.remove(link)
   for channel,(blue,red) in enumerate(zip((.012,.075,.32),(.578,.005,.028))):
    d=socket.driver_add('default_value',channel).driver;v=d.variables.new();v.name='x';v.targets[0].id=rig;v.targets[0].data_path='["MatchSide"]';d.expression=f'{blue}*(x==0)+{red}*(x==1)'
  index=len(o.data.materials);o.data.materials.append(material);uv=o.data.uv_layers.active.data
  for p in o.data.polygons:
   c=sum((uv[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.loop_indices)
   if 0<=c.x<.25 and .5<c.y<.75:p.material_index=index
def crowd_shoes(rig):
 import bmesh
 body=bpy.data.objects['Body'];names={g.index:g.name for g in body.vertex_groups}
 pieces=[]
 for side in 'lr':
  foot=rig.matrix_world@rig.data.bones['foot_'+side].head_local
  coordinates=[body.matrix_world@v.co for v in body.data.vertices if (body.matrix_world@v.co).z<foot.z+.06 and any(names[g.group] in ['foot_'+side,'ball_'+side] and g.weight>.1 for g in v.groups)]
  low=Vector(tuple(min(p[i] for p in coordinates) for i in range(3)));high=Vector(tuple(max(p[i] for p in coordinates) for i in range(3)))
  center=(low+high)*.5;rx=max(.05,(high.x-low.x)*.54);ry=max(.13,(high.y-low.y)*.54)
  verts=[];faces=[];segments=20
  for row,(z,taper,ankle) in enumerate([(.005,1,0),(.02,1,0),(.045,.98,.05),(.075,.88,.2),(.105,.7,.6),(.14,.5,1),(.165,.47,1)]):
   cx=center.x*(1-ankle)+foot.x*ankle;cy=center.y*(1-ankle)+foot.y*ankle
   for i in range(segments):
    a=math.tau*i/segments;c=math.cos(a);s=math.sin(a)
    verts.append((cx+rx*taper*math.copysign(abs(c)**.8,c),cy+ry*(1-ankle*.65)*math.copysign(abs(s)**.8,s),z*(foot.z/.08276)))
   if row:
    for i in range(segments):
     j=(i+1)%segments;faces.append(((row-1)*segments+i,(row-1)*segments+j,row*segments+j,row*segments+i))
  faces.append(tuple(reversed(range(segments))))
  data=bpy.data.meshes.new('Fitted_Shoe_'+side);data.from_pydata(verts,[],faces);data.update();o=bpy.data.objects.new('Shoe_'+side,data);bpy.context.scene.collection.objects.link(o)
  o.vertex_groups.new(name='foot_'+side).add(list(range(len(o.data.vertices))),1,'REPLACE');pieces.append(o)
 bpy.ops.object.select_all(action='DESELECT')
 for o in pieces:o.select_set(True)
 bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join();o=pieces[0];o.name='Crowd_TrainingShoes'
 mat=bpy.data.materials.new('Crowd_Shoe_Charcoal');mat.diffuse_color=(.018,.02,.025,1);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=mat.diffuse_color;bs.inputs['Roughness'].default_value=.65;o.data.materials.append(mat)
 for p in o.data.polygons:p.use_smooth=True
 suite.bind(o,rig)
 for m in body.modifiers:
  if m.type=='MASK' and 'FootGuards' in m.name:
   g=body.vertex_groups.get(m.vertex_group)
   if g:g.add([v.index for v in body.data.vertices if (body.matrix_world@v.co).z<.145*(foot.z/.08276)],1,'REPLACE')
 return o
def export(rig,meshes,path,animation=False):
 copies=[];update();deps=bpy.context.evaluated_depsgraph_get()
 for o in meshes:
  if o.hide_render:continue
  mods=[m for m in o.modifiers if m.type=='ARMATURE']
  for m in mods:m.show_viewport=False
  update();data=bpy.data.meshes.new_from_object(o.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
  c=o.copy();c.data=data;c.animation_data_clear();c.modifiers.clear();bpy.context.scene.collection.objects.link(c);c.hide_viewport=c.hide_render=False;c.hide_set(False);suite.weights(c,rig,2 if len(rig.data.bones)<30 else 4);copies.append(c)
  for m in mods:m.show_viewport=True
 bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
 for c in copies:c.select_set(True)
 bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},use_mesh_modifiers=False,add_leaf_bones=False,bake_anim=animation,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,path_mode='COPY',embed_textures=True,axis_forward='-Z',axis_up='Y')
 for c in copies:
  data=c.data;bpy.data.objects.remove(c,do_unlink=True);bpy.data.meshes.remove(data)
def run(kind):
 directory=OUT/kind;catalog=json.loads((directory/'catalog.json').read_text())
 for path in sorted(directory.glob('*.blend')):
  if '--crowds' in sys.argv and not path.stem.startswith('Crowd'):continue
  if '--fighters' in sys.argv and path.stem.startswith('Crowd'):continue
  bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_Body_'+kind];preview=path.stem=='Preview';crowd=path.stem.startswith('Crowd')
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
  for o in meshes:
   if not preview and o.name.startswith('Hair_'):
    o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(o.data.vertices))),1,'REPLACE')
   for m in o.modifiers:
    if m.type=='MASK':m.use_smooth=True
  # At coarse LODs the full trouser surface is needed to preserve coverage
  # during sitting; the overlaid jacket still conceals the waistband.
  if not preview:
   pants=bpy.data.objects['Pants']
   for m in list(pants.modifiers):
    if m.type=='MASK':
     for attr in ['show_viewport','show_render']:
      try:m.driver_remove(attr)
      except:pass
     pants.modifiers.remove(m)
   if not crowd:
    group=pants.vertex_groups.get('CoveredBy_Jacket') or pants.vertex_groups.new(name='CoveredBy_Jacket')
    height=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
    cutoff=(rig.matrix_world@rig.data.bones['pelvis'].head_local).z-.21*height
    for v in pants.data.vertices:group.add([v.index],max(0,min(1,.5+((pants.matrix_world@v.co).z-cutoff)/(.8*height))),'REPLACE')
    m=pants.modifiers.new('Jacket overlap','MASK');m.vertex_group=group.name;m.invert_vertex_group=True;m.use_smooth=True;m.threshold=.5
    for attr in ['show_viewport','show_render']:suite.driver(m,attr,rig,'Wear_Jacket','x')
  team_material(rig,meshes)
  if crowd:
   for o in list(meshes):
    if o.name.startswith(('FootGuards','Crowd_TrainingShoes','Belt')):meshes.remove(o);bpy.data.objects.remove(o,do_unlink=True)
   import bmesh
   for o in meshes:
    if o.name.startswith('Jacket') and not o.get('Crowd_Hem_Trimmed'):
     bm=bmesh.new();bm.from_mesh(o.data);z=(rig.matrix_world@rig.data.bones['pelvis'].head_local).z-.04
     point=o.matrix_world.inverted()@Vector((0,0,z));normal=o.matrix_world.to_3x3().transposed()@Vector((0,0,1))
     bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=point,plane_no=normal,clear_inner=True,dist=.00001)
     bm.to_mesh(o.data);bm.free();o['Crowd_Hem_Trimmed']=True
   rig['JacketStyle']=1
   if not bpy.data.materials.get('Crowd_Clothes_Top'):
    for category,names,color in [('Top',['Jacket'],(.065,.095,.15,1)),('Pants',['Pants'],(.045,.046,.05,1))]:
     mat=bpy.data.materials.new('Crowd_Clothes_'+category);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.85
     for o in meshes:
      if any(o.name.startswith(n) for n in names):
       o.data.materials.clear();o.data.materials.append(mat)
       for p in o.data.polygons:p.material_index=0
   meshes.append(crowd_shoes(rig))
   for o in meshes:suite.weights(o,rig,2)
   catalog['profiles'][path.stem]['animations']=actions(rig)
  rig.update_tag();bpy.context.scene.frame_set(1);update()
  bpy.context.scene.render.resolution_percentage=100
  bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
  if not preview:
   evaluated={};deps=bpy.context.evaluated_depsgraph_get()
   for o in meshes:
    if not o.hide_render:
     e=o.evaluated_get(deps);m=e.to_mesh();m.calc_loop_triangles();evaluated[o.name]=len(m.loop_triangles);e.to_mesh_clear()
   catalog['profiles'][path.stem]['visible_evaluated_triangles']=evaluated;catalog['profiles'][path.stem]['visible_total']=sum(evaluated.values())
   export(rig,meshes,directory/(path.stem+'_Sparring.fbx' if not crowd else path.stem+'.fbx'))
   if not crowd:
    for k in ['Helmet','Protector','Gloves','FootGuards']:rig['Wear_'+k]=False
    rig.update_tag();bpy.context.scene.frame_set(2);bpy.context.scene.frame_set(1);update();export(rig,meshes,directory/(path.stem+'_Dobok.fbx'))
   elif path.stem=='Crowd_Near':
    for name in catalog['profiles'][path.stem]['animations']:
     rig.animation_data.action=bpy.data.actions[name];export(rig,[],directory/(name+'.fbx'),True)
  suite.log(kind+' finalized '+path.stem)
 (directory/'catalog.json').write_text(json.dumps(catalog,indent=2))
if __name__=='__main__':
 try:
  args=[s for s in sys.argv[sys.argv.index('--')+1:] if s not in ['--crowds','--fighters']] if '--' in sys.argv else []
  args=args or ['Medium','Compact','Stocky','LeanTall','Tall']
  for kind in args:run(kind)
 except:
  (OUT/'finish_error.log').write_text(traceback.format_exc());raise
