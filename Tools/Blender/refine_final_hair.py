import bpy,sys,math,numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import repair_sparring_fit as fit
OUT=fit.ROOT/'Resources/Models/FinalRefinement';OUT.mkdir(exist_ok=True)
def seam(s):
 for o in s.objects:
  if o.type=='MESH' and o.name.startswith('Hair_'):
   for mat in o.data.materials:
    if mat and mat.use_nodes:
     for n in mat.node_tree.nodes:
      if n.type=='TEX_IMAGE':n.extension='REPEAT'
def pony(s,r):
 states={o:o.data.pose_position for o in s.objects if o.type=='ARMATURE'}
 for o in states:o.data.pose_position='REST'
 bpy.context.view_layer.update();tree=fit.tree(bpy.data.objects['Head'],True);scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 roots=[]
 for helmet in [False,True]:
  z=(1.555 if helmet else 1.665)*scale;hit=tree.ray_cast(Vector((0,.5*scale,z)),Vector((0,-1,0)))[0];roots.append(Vector((0,(hit.y if hit is not None else .08*scale)+.009*scale,z)))
 coarse=len(r.data.bones)==25;rings=14 if coarse else 28;cols=12 if coarse else 32
 def point(t,a,helmet,extra=0):
  root=roots[int(helmet)];center=root+Vector((.008*math.sin(t*3),(.085 if helmet else .055)*t**.8,-.18*t))*scale;radius=(.019*(1-.25*t)*(1-.55*max(0,(t-.88)/.12))+.001)*scale
  return center+Vector(((radius+extra)*math.cos(a),(radius+extra)*.75*math.sin(a),0))
 def replace(o,verts,faces,fitted,uvs):
  mats=list(o.data.materials);me=bpy.data.meshes.new(o.name+'_Refined');me.from_pydata([o.matrix_world.inverted()@p for p in verts],[],[tuple(reversed(face)) for face in faces] if 'Hair_Tie' not in o.name else faces);me.update();o.data=me
  for mat in mats:me.materials.append(mat)
  for poly in me.polygons:poly.use_smooth=True
  uv=me.uv_layers.new(name='UVMap')
  for poly in me.polygons:
   for li in poly.loop_indices:uv.data[li].uv=uvs[me.loops[li].vertex_index]
   values=[uv.data[li].uv.x for li in poly.loop_indices]
   if max(values)-min(values)>.5:
    for li in poly.loop_indices:
     if uv.data[li].uv.x<.5:uv.data[li].uv.x+=1
  o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(verts))),1,'REPLACE');o.shape_key_add(name='Basis');key=o.shape_key_add(name='HelmetFit')
  for v,p in zip(key.data,fitted):v.co=o.matrix_world.inverted()@p
  d=key.driver_add('value').driver;var=d.variables.new();var.name='helmet';var.targets[0].id=r;var.targets[0].data_path='["Wear_Helmet"]';d.expression='1 if helmet else 0'
 for suffix in ['Ponytail_Core','Ponytail']:
  o=bpy.data.objects.get('Hair_Low_Ponytail__'+suffix)
  if not o:continue
  verts=[];fitted=[];faces=[];uvs=[]
  if suffix=='Ponytail_Core':
   for j in range(rings+1):
    for i in range(cols):
     t=j/rings;a=math.tau*i/cols;verts.append(point(t,a,False));fitted.append(point(t,a,True));uvs.append((i/cols,.01+.98*t))
   for j in range(rings):
    for i in range(cols):faces.append((j*cols+i,j*cols+(i+1)%cols,(j+1)*cols+(i+1)%cols,(j+1)*cols+i))
  else:
   strands=18 if coarse else 64
   for i in range(strands):
    start=len(verts);phase=math.tau*i/strands
    for j in range(rings+1):
     t=j/rings;a=phase+.10*math.sin(t*4+i*.4)
     for edge in [-1,1]:
      aa=a+edge*.008;verts.append(point(t,aa,False,.00035*scale));fitted.append(point(t,aa,True,.00035*scale));uvs.append(((edge+1)/2,.01+.98*t))
     if j:faces.append((start+(j-1)*2,start+(j-1)*2+1,start+j*2+1,start+j*2))
  replace(o,verts,faces,fitted,uvs)
 o=bpy.data.objects.get('Hair_Low_Ponytail__Hair_Tie')
 if o:
  verts=[];fitted=[];faces=[];uvs=[]
  for i in range(32):
   a=math.tau*i/32
   for j in range(8):
    b=math.tau*j/8
    for target,helmet in [(verts,False),(fitted,True)]:target.append(roots[int(helmet)]+Vector(((.021+.002*math.cos(b))*math.cos(a),(.016+.002*math.cos(b))*math.sin(a),.002*math.sin(b)))*scale)
    uvs.append((i/32,j/8))
  for i in range(32):
   for j in range(8):faces.append((i*8+j,((i+1)%32)*8+j,((i+1)%32)*8+(j+1)%8,i*8+(j+1)%8))
  replace(o,verts,faces,fitted,uvs)
 for o,state in states.items():o.data.pose_position=state
 bpy.context.view_layer.update()

def texture_finish(s):
 name='HairFiber_TangentNormal';img=bpy.data.images.get(name)
 if not img:
  w,h=1024,256;y,x=np.mgrid[0:h,0:w];u=x/w;v=y/h
  phase=np.sin(v*math.tau*3)*.5;dx=.28*np.sin(u*math.tau*127+phase)+.13*np.sin(u*math.tau*251-phase)+.08*np.sin(u*math.tau*53)
  dy=.035*np.sin(v*math.tau*7+u*math.tau*11);z=np.sqrt(np.maximum(.01,1-dx*dx-dy*dy));rgba=np.ones((h,w,4),dtype=np.float32);rgba[:,:,0]=(dx+1)/2;rgba[:,:,1]=(dy+1)/2;rgba[:,:,2]=(z+1)/2;end=.82+.14*(.5+.5*np.sin(u*math.tau*43));rgba[:,:,3]=np.clip((end-v)/.08,0,1);rgba[0,:,3]=0
  img=bpy.data.images.new(name,width=w,height=h,alpha=True);img.colorspace_settings.name='Non-Color';img.pixels.foreach_set(rgba.ravel());img.filepath_raw=str(OUT/(name+'.png'));img.file_format='PNG';img.save();img.pack()
 seen=set();copies={}
 for o in s.objects:
  if o.type!='MESH' or not o.name.startswith(('Hair_Side_Part','Hair_Chin_Length_Bob','Hair_Low_Ponytail','Hair_Compact_Bun')) or 'Hair_Tie' in o.name:continue
  if not o.data.uv_layers:continue
  for index,original in enumerate(list(o.data.materials)):
   is_tail=any(x in o.name for x in ['__Ponytail_Core','__Ponytail'])
   key=(original,is_tail)
   mat=copies.get(key)
   if mat is None:
    mat=original.copy();mat.name='FiberFinish_'+original.name+('_Tail' if is_tail else '');copies[key]=mat
   o.data.materials[index]=mat
   if not mat or not mat.use_nodes or mat in seen:continue
   seen.add(mat);nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
   if not bs:continue
   tex=nodes.new('ShaderNodeTexImage');tex.name='Portable Hair Fiber Normal';tex.image=img;tex.extension='REPEAT';normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.45;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal']);bs.inputs['Roughness'].default_value=.65
   if is_tail:
    links.new(tex.outputs['Alpha'],bs.inputs['Alpha']);mat.surface_render_method='DITHERED'

if __name__=='__main__':
 import audit_sparring_styles as a
 bpy.ops.wm.open_mainfile(filepath=str(fit.ROOT/'Resources/Models/CharacterSuite/Medium/Gameplay_High.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];seam(s);pony(s,r);texture_finish(s);r.animation_data.action=None
 for t in r.animation_data.nla_tracks:t.mute=True
 r['HairStyle']=4;r['Wear_Protector']=False;r['Wear_Helmet']=False;a.build.refresh(r);a.audit.pose(r,'Neutral',1);s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
 for helmet in [False,True]:
  r['Wear_Helmet']=helmet;a.build.refresh(r);a.render(s,r,1,OUT,'Pony_V3_'+str(helmet),(.5,1,1.8),(0,.02,1.62),.6,600,600)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Pony_Pilot.blend'),compress=True)
