"""Background-only modular character library and configurable PC/console LOD builder."""
import bpy, math, json, sys, traceback
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Resources/Models/CharacterSuite'
OUT.mkdir(parents=True,exist_ok=True)
LOG=OUT/'build.log'
PARTS=['Body','Head','Hair_Buzzcut','Jacket','Pants','Belt','Protector','Helmet','Gloves','FootGuards']
PROFILES={
 'Gameplay_High':[20000,28000,16000,15200,12018,2852,15702,40000,10000,10000],
 'Gameplay_Mid':[10000,14000,6000,9000,7000,1800,10000,22000,6000,6000],
 'Gameplay_Far':[5000,6000,2000,4500,3500,900,5000,10000,3000,3000],
 'Crowd_Near':[2200,2400,900,2400,1800,400,0,0,0,800],
 'Crowd_Far':[800,700,250,750,600,180,0,0,0,350]}
KEEP={'root','pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head'}|{f'{b}_{s}' for s in 'lr' for b in ['clavicle','upperarm','lowerarm','hand','thigh','calf','foot','ball']}
def log(s):
 with LOG.open('a') as f:f.write(str(s)+'\n')
def update():
 bpy.context.view_layer.update()
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def tris(o):
 o.data.calc_loop_triangles();return len(o.data.loop_triangles)
def driver(owner,path,rig,prop,expression):
 try:owner.driver_remove(path)
 except:pass
 d=owner.driver_add(path).driver;d.type='SCRIPTED';v=d.variables.new();v.name='x';v.targets[0].id=rig;v.targets[0].data_path='["'+prop+'"]';d.expression=expression
def bind(o,rig):
 for m in list(o.modifiers):
  if m.type=='ARMATURE':o.modifiers.remove(m)
 w=o.matrix_world.copy();o.parent=rig;o.matrix_world=w
 m=o.modifiers.new('Deform','ARMATURE');m.object=rig
def decimate(o,budget):
 if o.name.startswith('Hair_'):
  import bmesh
  # Disconnected strands cannot be collapsed effectively. Thin whole strands,
  # then add a fitted scalp surface so reduced density never reveals holes.
  bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);components=[]
  for seed in list(bm.verts):
   if seed not in remaining:continue
   remaining.remove(seed);stack=[seed];component=[]
   while stack:
    v=stack.pop();component.append(v)
    for e in v.link_edges:
     n=e.other_vert(v)
     if n in remaining:remaining.remove(n);stack.append(n)
   components.append(component)
  stride=max(1,math.ceil(tris(o)/max(1,budget*.55)))
  removed=[v for i,c in enumerate(components) if i%stride for v in c]
  bmesh.ops.delete(bm,geom=removed,context='VERTS');bm.to_mesh(o.data);bm.free()
  if not o.name.endswith('Bald'):
   head=bpy.data.objects['Head'];cap=duplicate(head,'TemporaryScalp');cap.animation_data_clear()
   cap.modifiers.clear();bm=bmesh.new();bm.from_mesh(cap.data)
   top=max((cap.matrix_world@v.co).z for v in bm.verts)
   bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0 or any((cap.matrix_world@v.co).z < top-(.067 if (cap.matrix_world@v.co).y<-.018 else .14) for v in f.verts)],context='FACES')
   bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
   for v in bm.verts:v.co+=v.normal*.0012
   bm.to_mesh(cap.data);bm.free();cap.data.materials.clear()
   for mat in o.data.materials:cap.data.materials.append(mat)
   decimate(cap,max(100,int(budget*.4)))
   # Join data directly; this avoids hidden-object selection and driver context.
   bm=bmesh.new();bm.from_mesh(o.data);offset=len(bm.verts);bm.from_mesh(cap.data);bm.verts.ensure_lookup_table()
   transform=o.matrix_world.inverted()@cap.matrix_world
   for v in list(bm.verts)[offset:]:v.co=transform@v.co
   bm.to_mesh(o.data);bm.free();bpy.data.objects.remove(cap,do_unlink=True)
  o.vertex_groups.clear();g=o.vertex_groups.new(name='head');g.add(list(range(len(o.data.vertices))),1,'REPLACE')
  return
 n=tris(o)
 if n<=budget:return
 active(o);states=[(m,m.show_viewport) for m in o.modifiers]
 for m,_ in states:m.show_viewport=False
 m=o.modifiers.new('LOD reduction','DECIMATE');m.ratio=budget/n;m.use_collapse_triangulate=True
 bpy.ops.object.modifier_apply(modifier=m.name)
 for m,state in states:
  m.show_viewport=state
  if m.type=='MASK':m.use_smooth=True
def weights(o,rig,limit):
 names={g.index:g.name for g in o.vertex_groups};valid=set(rig.data.bones.keys())
 rows=[]
 for v in o.data.vertices:
  w={}
  for g in v.groups:
   n=names[g.group]
   if n.startswith('Coverage'):continue
   if n not in valid:
    n='head' if o.name.startswith(('Head','Hair')) else None
   if n:w[n]=w.get(n,0)+g.weight
  row=sorted(w.items(),key=lambda x:-x[1])[:limit];total=sum(w for n,w in row)
  rows.append([(n,w/total) for n,w in row] if total else [('pelvis',1)])
 for g in list(o.vertex_groups):
  if g.name in valid or g.name.startswith('FACIAL'):o.vertex_groups.remove(g)
 groups={n:o.vertex_groups.get(n) or o.vertex_groups.new(name=n) for row in rows for n,w in row}
 for i,row in enumerate(rows):
  for n,w in row:groups[n].add([i],w,'REPLACE')
 bind(o,rig)
def duplicate(o,name):
 c=o.copy();c.data=o.data.copy();c.name=name;bpy.context.scene.collection.objects.link(c);c.animation_data_clear();return c
def alternatives(rig):
 specs={'Head':['Oval','BroadJaw','NarrowJaw'],'Hair_Buzzcut':['Buzz','ShortCrop','Bald'],'Jacket':['WhiteWrap','WhiteVNeck'],'Protector':['Contoured','Padded'],'Helmet':['OpenFace','ThickPadding'],'Gloves':['Standard','PaddedKnuckle'],'FootGuards':['SensorSocks','PaddedInstep']}
 catalog={}
 for part,styles in specs.items():
  original=bpy.data.objects[part];prop=part.replace('Hair_Buzzcut','Hair')+'Style';rig[prop]=0;rig.id_properties_ui(prop).update(min=0,max=len(styles)-1,description=' / '.join(f'{i}: {s}' for i,s in enumerate(styles)))
  catalog[part]=[]
  for i,style in enumerate(styles):
   o=original if i==0 else duplicate(original,part+'_'+style)
   if i and part=='Head':
    zmax=max(v.co.z for v in o.data.vertices);zmin=min(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:
     t=(v.co.z-zmin)/max(zmax-zmin,1e-6);v.co.x*=1+(0.065 if i==1 else -.05)*math.exp(-((t-.28)/.18)**2)
   elif i and part=='Hair_Buzzcut':
    if style=='Bald':
     # Keep eyebrows, omit scalp strands using world-space height relative to head.
     import bmesh
     bm=bmesh.new();bm.from_mesh(o.data);top=max((o.matrix_world@v.co).z for v in bm.verts)
     bmesh.ops.delete(bm,geom=[v for v in bm.verts if (o.matrix_world@v.co).z>top-.105],context='VERTS');bm.to_mesh(o.data);bm.free()
    else:
     center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
     for v in o.data.vertices:
      if v.co.z>center.z:v.co+=Vector((0,0,.005))
   elif i and part=='Jacket':
    # Remove the disconnected diagonal wrap strip; retain white neckline and skirt.
    import bmesh
    bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);components=[]
    while remaining:
     stack=[remaining.pop()];component=[]
     while stack:
      v=stack.pop();component.append(v)
      for e in v.link_edges:
       n=e.other_vert(v)
       if n in remaining:remaining.remove(n);stack.append(n)
     components.append(component)
    for c in components:
     if 60<=len(c)<=110:bmesh.ops.delete(bm,geom=c,context='VERTS')
    bm.to_mesh(o.data);bm.free()
   elif i:
    o.data.update()
    for v in o.data.vertices:v.co+=v.normal*.0018
   catalog[part].append({'style':style,'object':o.name})
   # Combine style choice with the existing wardrobe toggle.
   wear='Wear_Hair' if part=='Hair_Buzzcut' else 'Wear_'+part
   for path in ['hide_render','hide_viewport']:
    driver(o,path,rig,prop,f'x != {i}')
    if wear in rig:
     d=o.animation_data.drivers.find(path).driver;v=d.variables.new();v.name='w';v.targets[0].id=rig;v.targets[0].data_path='["'+wear+'"]';d.expression=f'(x != {i}) or (not w)'
 return catalog
def palette(rig):
 palettes={'SkinTone':['F6EDE4','F3E7DB','F7EAD0','EADABA','D7BD96','A07E56','825C43','604134','3A312A','292420'],'HairColor':['17120F','35251C','60402B','783C26','B39762','77736E','D8D5CD'],'EyeColor':['25180F','573620','9B6B25','787038','426344','426B85','7B8588']}
 def rgb(h):
  a=[int(h[i:i+2],16)/255 for i in (0,2,4)];return [x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in a]
 seen=set()
 for prop,colors in palettes.items():
  rig[prop]=5 if prop=='SkinTone' else 0;rig.id_properties_ui(prop).update(min=0,max=len(colors)-1)
  for o in bpy.data.objects:
   if o.type!='MESH':continue
   for mat in o.data.materials:
    if not mat or not mat.use_nodes or (mat.name,prop) in seen:continue
    name=mat.name.lower();nodes=mat.node_tree.nodes;links=mat.node_tree.links
    if not ((prop=='SkinTone' and 'skin' in name) or (prop=='HairColor' and ('hair' in name or 'brow' in name)) or (prop=='EyeColor' and 'eye' in name and 'lash' not in name)):continue
    seen.add((mat.name,prop));bs=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not bs:continue
    socket=bs.inputs['Base Color']
    if prop=='EyeColor':
     mix=next((n for n in nodes if n.type=='MIX' and n.data_type=='RGBA'),None)
     if not mix:continue
     socket=mix.inputs[7]
    tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
    if socket.is_linked:links.new(socket.links[0].from_socket,tint.inputs[1])
    else:tint.inputs[1].default_value=(1,1,1,1)
    links.new(tint.outputs[0],socket)
    for channel in range(3):
     d=tint.inputs[2].driver_add('default_value',channel).driver;v=d.variables.new();v.name='x';v.targets[0].id=rig;v.targets[0].data_path='["'+prop+'"]'
     reference=rgb('A07E56')[channel] if prop=='SkinTone' else 1
     d.expression='+'.join(f'{rgb(c)[channel]/reference:.6f}*(x=={i})' for i,c in enumerate(colors))
 return palettes
def reduce_rig(rig,objects):
 mapping={}
 for b in rig.data.bones:
  p=b
  while p and p.name not in KEEP:p=p.parent
  mapping[b.name]=p.name if p else 'pelvis'
 for o in objects:
  names={g.index:g.name for g in o.vertex_groups};rows=[]
  for v in o.data.vertices:
   row={}
   for g in v.groups:
    if names[g.group] in mapping:
     n=mapping[names[g.group]];row[n]=row.get(n,0)+g.weight
   rows.append(row)
  for g in list(o.vertex_groups):
   if g.name in mapping:o.vertex_groups.remove(g)
  groups={n:o.vertex_groups.get(n) or o.vertex_groups.new(name=n) for row in rows for n in row}
  for i,row in enumerate(rows):
   for n,w in row.items():groups[n].add([i],w,'REPLACE')
 active(rig);bpy.ops.object.mode_set(mode='EDIT')
 for b in list(rig.data.edit_bones):
  if b.name not in KEEP:rig.data.edit_bones.remove(b)
 bpy.ops.object.mode_set(mode='OBJECT')
 for o in objects:weights(o,rig,2)
def crowd_actions(rig):
 result=[]
 rig.animation_data.action=None
 for tr in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(tr)
 for label in ['StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave']:
  rig.animation_data.action=None
  for frame in range(1,62,3):
   t=(frame-1)/60*2*math.pi
   for p in rig.pose.bones:p.matrix_basis=Matrix();p.rotation_mode='QUATERNION'
   def rotate(name,axis,angle):
    p=rig.pose.bones.get(name)
    if p:p.rotation_quaternion=Quaternion(p.bone.matrix_local.to_quaternion().inverted()@Vector(axis),angle)
   if label.startswith('Seated'):
    p=rig.pose.bones['pelvis'];p.location=p.bone.matrix_local.to_3x3().inverted()@Vector((0,0,-.43))
    for s in 'lr':rotate('thigh_'+s,(1,0,0),-math.pi/2);rotate('calf_'+s,(1,0,0),math.pi/2)
   rotate('spine_03',(0,1,0),.018*math.sin(t))
   for s,sign in [('l',1),('r',-1)]:
    rotate('upperarm_'+s,(0,1,0),sign*.95)
    rotate('lowerarm_'+s,(0,0,1),sign*.12)
    if label=='Cheer':rotate('upperarm_'+s,(0,1,0),-sign*(1.25+.1*math.sin(t)));rotate('lowerarm_'+s,(0,0,1),sign*.55)
    if label=='SeatedClap':rotate('upperarm_'+s,(0,0,1),sign*.65);rotate('lowerarm_'+s,(0,0,1),sign*(1.1+.12*math.cos(t*2)))
   if label=='Wave':rotate('upperarm_r',(0,1,0),1.3);rotate('lowerarm_r',(0,0,1),-.8);rotate('hand_r',(0,1,0),.35*math.sin(t*2))
   for p in rig.pose.bones:
    p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name);p.keyframe_insert('location',frame=frame,group=p.name)
  a=rig.animation_data.action;a.name='Crowd_'+label;a.use_fake_user=True;result.append(a.name)
 rig.animation_data.action=None
 for p in rig.pose.bones:p.matrix_basis=Matrix()
 bpy.context.scene.frame_end=61
 return result
def build(kind):
 log(kind+' START')
 source=ROOT/f'Resources/Models/Animation/OpenStance_{kind}_Animation.blend'
 dest=OUT/kind;dest.mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects[f'RIG_Body_{kind}']
 variants=alternatives(rig);log(kind+' variants ready');colors=palette(rig)
 bpy.ops.wm.save_as_mainfile(filepath=str(dest/'Preview.blend'),compress=True)
 manifest={'body_type':kind,'preview':'Preview.blend','variants':variants,'palettes':colors,'profiles':{}}
 for profile,budgets in PROFILES.items():
  bpy.ops.wm.open_mainfile(filepath=str(dest/'Preview.blend'));rig=bpy.data.objects[f'RIG_Body_{kind}'];crowd=profile.startswith('Crowd')
  rig.animation_data.action=None
  for p in rig.pose.bones:p.matrix_basis=Matrix()
  meshes=[]
  for part,budget in zip(PARTS,budgets):
   candidates=[bpy.data.objects[e['object']] for e in variants.get(part,[{'object':part}])]
   for o in candidates:
    if not budget:bpy.data.objects.remove(o,do_unlink=True);continue
    weights(o,rig,4);decimate(o,budget);weights(o,rig,4);meshes.append(o)
  face=bpy.data.objects.get(f'RIG_Face_{kind}')
  if face:bpy.data.objects.remove(face,do_unlink=True)
  animations=[]
  if crowd:
   reduce_rig(rig,meshes);animations=crowd_actions(rig)
   for o in list(bpy.data.objects):
    if o.type=='EMPTY' and 'MarkerLabel' in o:bpy.data.objects.remove(o,do_unlink=True)
  for key in ['Wear_Helmet','Wear_Protector','Wear_Gloves']:rig[key]=not crowd
  rig['Wear_FootGuards']=True;rig.update_tag();update()
  counts={o.name:tris(o) for o in meshes}
  # Counts are base mesh triangles; evaluated totals include coverage and thickness.
  evaluated={}
  deps=bpy.context.evaluated_depsgraph_get()
  for o in meshes:
   if not o.hide_render:
    data=o.evaluated_get(deps).to_mesh();data.calc_loop_triangles();evaluated[o.name]=len(data.loop_triangles);o.evaluated_get(deps).to_mesh_clear()
  report={'base_triangles':counts,'visible_evaluated_triangles':evaluated,'visible_total':sum(evaluated.values()),'bones':len(rig.data.bones),'animations':animations,'influence_limit':2 if crowd else 4}
  manifest['profiles'][profile]=report
  bpy.ops.wm.save_as_mainfile(filepath=str(dest/(profile+'.blend')),compress=True)
  log((kind,profile,report['visible_total']))
 (dest/'catalog.json').write_text(json.dumps(manifest,indent=2))
 log(kind+' DONE')
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Medium','Compact','Stocky','LeanTall','Tall']
  for kind in args:build(kind)
 except:log(traceback.format_exc());raise
