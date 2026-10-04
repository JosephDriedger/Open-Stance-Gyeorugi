"""Editable adult character presets and fitted hairstyle meshes, background only."""
import bpy,bmesh,math,random,json,sys,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as base
import rebuild_reference_helmets as u
import build_character_suite as suite
OUT=base.ROOT/'Resources/Models/CharacterVariations';OUT.mkdir(exist_ok=True)
STYLES=['Crew_Cut','Side_Part','Curly_Crop','Chin_Length_Bob','Low_Ponytail','Compact_Bun']
PRESETS=[('Male_Athletic',.15,.02,-.02,.19,0),('Male_Lean',.07,-.07,-.035,.13,1),('Female_Athletic',.015,-.06,.075,-.045,4),('Female_Strong',.055,.015,.11,.015,2)]
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
def material(rig):
 m=bpy.data.materials.new('Natural_Hair');m.use_nodes=True;n=m.node_tree.nodes;b=n.get('Principled BSDF');b.inputs['Roughness'].default_value=.46
 b.inputs['Metallic'].default_value=0;b.inputs['Roughness'].default_value=.64
 colors=[(.006,.004,.003),(.018,.009,.004),(.060,.027,.011),(.12,.030,.010),(.22,.14,.055),(.20,.19,.175),(.52,.48,.39)]
 for c in range(3):
  d=b.inputs['Base Color'].driver_add('default_value',c).driver;v=d.variables.new();v.name='x';v.targets[0].id=rig;v.targets[0].data_path='["HairColor"]';d.expression='+'.join(f'{col[c]}*(x=={i})' for i,col in enumerate(colors))
 noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=350
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.00035;m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],b.inputs['Normal'])
 return m
def warp_all(preset):
 name,shoulders,waist,hips,jaw,_=preset
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not any(m.type=='ARMATURE' for m in o.modifiers):continue
  mw=np.array(o.matrix_world);inv=np.linalg.inv(mw)
  def transform(collection):
   co=np.empty(len(collection)*3,dtype=np.float32);collection.foreach_get('co',co);co=co.reshape(-1,3)
   w=co@mw[:3,:3].T+mw[:3,3];x,y,z=w.T.copy()
   chest=np.exp(-((z-1.31)/.135)**2);mid=np.exp(-((z-1.10)/.11)**2);hip=np.exp(-((z-.88)/.14)**2)
   torso=np.exp(-(np.abs(x)/.31)**6)
   width=1+torso*(shoulders*chest+waist*mid+hips*hip)
   face=np.exp(-((z-1.575)/.042)**2)*np.clip((-y-.015)/.07,0,1)
   w[:,0]=x*width*(1+jaw*face)
   # A modest front/back change follows the same clothing and equipment volume.
   w[:,1]=y*(1+torso*(.35*shoulders*chest+.40*waist*mid+.30*hips*hip))
   if name.startswith('Male'):
    w[:,1]-=.005*np.exp(-((z-1.674)/.016)**2)*np.exp(-(x/.065)**4)*np.clip((-y-.06)/.04,0,1)
    w[:,1]-=.007*np.exp(-((z-1.550)/.025)**2)*np.exp(-(x/.040)**4)*np.clip((-y-.06)/.04,0,1)
   local=w@inv[:3,:3].T+inv[:3,3]
   collection.foreach_set('co',local.astype(np.float32).ravel())
  if o.data.shape_keys:
   for key in o.data.shape_keys.key_blocks:transform(key.data)
  else:transform(o.data.vertices)
  o.data.update()

class Hair:
 def __init__(self,head):
  vs=[head.matrix_world@v.co for v in head.data.vertices];self.bvh=BVHTree.FromPolygons(vs,[tuple(p.vertices) for p in head.data.polygons]);self.center=Vector((0,.002,1.650))
 def limit(self,a):
  angle=abs(math.atan2(math.sin(a),math.cos(a)))
  knots=[(0,1.29),(.35,1.27),(.70,1.22),(1.0,1.46),(1.35,1.55),(1.70,1.72),(math.pi,1.86)]
  for (x,p),(y,q) in zip(knots,knots[1:]):
   if x<=angle<=y:
    t=(angle-x)/(y-x);t=t*t*(3-2*t);return p+(q-p)*t
  return 1.86
 def point(self,a,p,style):
  d=Vector((math.sin(p)*math.sin(a),-math.sin(p)*math.cos(a),math.cos(p)))
  hit=self.bvh.ray_cast(self.center,d)[0]
  if hit is None:hit=self.center+Vector((d.x*.082,d.y*.105,d.z*.103))
  lift=[.0025,.020,.010,.010,.0038,.0038][style]
  amount=.0018+lift*max(0,math.cos(p))**1.3
  q=hit+d*amount
  if style==1:
   q.x+=.013*max(0,math.cos(p))**2
   q.z+=.007*max(0,math.cos(p))*max(0,math.cos(a))
  if style==3:
   side=max(0,min(1,(abs(math.sin(a))+.8*max(0,-math.cos(a))-.35)/.5))
   q.z-=.112*side*(p/self.limit(a))**5
   q.x+=math.copysign(.026*side*(p/self.limit(a))**3,q.x)
  return q
def strands_mesh(name,paths,mat,radius=.00048):
 vs=[];fs=[];sides=5
 for points in paths:
  start=len(vs)
  for i,p in enumerate(points):
   tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();n=tangent.cross(Vector((0,1,0)))
   if n.length<.05:n=tangent.cross(Vector((1,0,0)))
   n.normalize();b=tangent.cross(n);r=radius*(1-.75*(i/(len(points)-1))**5)
   for k in range(sides):vs.append(p+r*(n*math.cos(math.tau*k/sides)+b*math.sin(math.tau*k/sides)))
   if i:
    for k in range(sides):a=start+(i-1)*sides+k;fs.append((a,start+(i-1)*sides+(k+1)%sides,start+i*sides+(k+1)%sides,start+i*sides+k))
 return u.mesh(name,vs,fs,mat)
def build_hair(fit,style,mat):
 n=128;rows=36;vs=[];fs=[]
 for j in range(rows+1):
  for i in range(n):
   a=math.tau*i/n;p=.001+(fit.limit(a)-.001)*j/rows;vs.append(fit.point(a,p,style))
 for j in range(rows):
  for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 cap=u.mesh('Scalp_Coverage',vs,fs,mat);m=cap.modifiers.new('Scalp thickness','SOLIDIFY');m.thickness=.0015;u.apply(cap,m)
 parts=[cap];rng=random.Random(300+style);paths=[]
 for i in range(9000 if style==0 else 1800):
  a=rng.random()*math.tau;p0=.08+rng.random()*.35;p1=fit.limit(a)*( .80+.20*rng.random());path=[]
  if style==0:
   p0=.02+rng.random()*(fit.limit(a)-.06);p1=p0+.018+rng.random()*.02
  steps=5 if style==0 else 18
  for j in range(steps):
   t=j/(steps-1);p=p0+(p1-p0)*t;aa=a+( .48*math.sin(math.pi*t) if style==1 else (0 if style==0 else .035*math.sin(t*math.pi)))
   q=fit.point(aa,p,style);q+=(q-fit.center).normalized()*.001
   path.append(q)
  paths.append(path)
 parts.append(strands_mesh('Combed_Hair_Fibers',paths,mat,.00023 if style!=0 else .00016))
 if style==2:
  curls=[]
  for i in range(2400):
   a=rng.random()*math.tau;p=.05+rng.random()*fit.limit(a)*.98;c=fit.point(a,p,style);normal=(c-fit.center).normalized();x=normal.cross(Vector((0,1,0))).normalized();y=normal.cross(x);radius=.0016+rng.random()*.0018
   phase=rng.random()*math.tau;tilt=(normal*.65+y*.35).normalized()
   curls.append([c+tilt*(.0005+.008*j/24)+radius*(x*math.cos(phase+j*math.tau*1.8/24)+y*math.sin(phase+j*math.tau*1.8/24)) for j in range(25)])
  parts.append(strands_mesh('Short_Textured_Curls',curls,mat,.00032))
 if style in [4,5]:
  paths=[]
  for i in range(420):
   a=rng.random()*math.tau;r=.003+.020*math.sqrt(rng.random());path=[]
   for j in range(28):
    t=j/27
    if style==4:q=Vector((r*math.cos(a)*(1-.65*t)+.012*math.sin(t*4),.107+.048*math.sin(math.pi*t/2)+r*math.sin(a),1.665-.175*t))
    else:
     angle=a+math.tau*t*1.4;q=Vector(((.030+r*.25)*math.cos(angle)*math.sin(math.pi*t),.110+.034*math.sin(math.pi*t)+r*.2*math.sin(angle),1.680+.032*math.sin(angle)*math.sin(math.pi*t)))
    path.append(q)
   paths.append(path)
  parts.append(strands_mesh('Ponytail' if style==4 else 'Coiled_Bun',paths,mat,.00115))
  if style==5:
   verts=[];faces=[];rings=24;cols=48
   for j in range(rings+1):
    p=.001+(math.pi-.002)*j/rings
    for i in range(cols):
     a=math.tau*i/cols;verts.append((.029*math.sin(p)*math.cos(a),.127+.022*math.sin(p)*math.sin(a),1.680+.029*math.cos(p)))
   for j in range(rings):
    for i in range(cols):faces.append((j*cols+i,j*cols+(i+1)%cols,(j+1)*cols+(i+1)%cols,(j+1)*cols+i))
   parts.append(u.mesh('Coiled_Bun_Core',verts,faces,mat))
  tie=bpy.data.materials.get('Hair_Tie')
  if not tie:tie=bpy.data.materials.new('Hair_Tie')
  tie.diffuse_color=(.01,.01,.012,1);tie.use_nodes=True;tie.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.01,.01,.012,1)
  parts.append(u.tube('Hair_Tie',[(.023*math.cos(math.tau*i/48),.111+.023*math.sin(math.tau*i/48),1.666) for i in range(49)],.003,tie))
 return parts

def eyebrows(fit,mat,male):
 # Dense fine fibers follow the facial surface instead of a row of thick dashes.
 paths=[];rng=random.Random(88)
 for sign in [-1,1]:
  for i in range(660 if male else 560):
   t=rng.betavariate(1.25,1.65)
   def center(q):return 1.651+.0048*math.sin(math.pi*q)-.003*q
   width=(.0048 if male else .0038)*(1-.87*t**1.6)
   x=.013+.044*t;z=center(t)+rng.uniform(-.5,.5)*width
   length=rng.uniform(.0027,.0048)*(1-.35*t)
   angle=math.radians(65*(1-t)**2-13*t)
   path=[]
   for j in range(6):
    s=j/5;xx=x+length*math.cos(angle)*s
    zz=z+length*math.sin(angle)*s-.0004*s*s
    hit,normal,_,_=fit.bvh.ray_cast(Vector((sign*xx,-.30,zz)),Vector((0,1,0)))
    if hit is None:break
    path.append(hit+normal*(.00009+.00012*math.sin(math.pi*s)))
   if len(path)==6:paths.append(path)
 browmat=mat.copy();browmat.name='Natural_Eyebrows'
 shader=browmat.node_tree.nodes.get('Principled BSDF')
 for link in list(browmat.node_tree.links):
  if link.to_socket==shader.inputs['Normal']:browmat.node_tree.links.remove(link)
 shader.inputs['Roughness'].default_value=.72
 o=strands_mesh('Eyebrows',paths,browmat,.000070 if male else .000060)
 o['GroomVersion']=2;o['FiberCount']=len(paths)
 return o

def bind_eyebrows(o,head):
 # Inherit nearby facial skin weights so brows participate in facial animation.
 from mathutils.kdtree import KDTree
 tree=KDTree(len(head.data.vertices))
 for v in head.data.vertices:tree.insert(head.matrix_world@v.co,v.index)
 tree.balance();groups={g.index:o.vertex_groups.new(name=g.name) for g in head.vertex_groups}
 for v in o.data.vertices:
  weights={}
  for _,index,distance in tree.find_n(o.matrix_world@v.co,3):
   influence=1/max(distance,.0001)**2
   for g in head.data.vertices[index].groups:weights[g.group]=weights.get(g.group,0)+g.weight*influence
  strongest=sorted(weights.items(),key=lambda item:item[1],reverse=True)[:4];total=sum(w for _,w in strongest)
  assert total>0,'Unweighted eyebrow vertex'
  for index,w in strongest:groups[index].add([v.index],w/total,'REPLACE')
 for source in head.modifiers:
  if source.type=='ARMATURE':
   mod=o.modifiers.new('Facial skin deformation','ARMATURE');mod.object=source.object;mod.use_deform_preserve_volume=source.use_deform_preserve_volume

def helmet_fit(o,fit,rig):
 o.shape_key_add(name='Basis');key=o.shape_key_add(name='HelmetFit')
 external=any(s in o.name for s in ['__Ponytail','__Coiled_Bun','__Hair_Tie'])
 if external:
  bun='Compact_Bun' in o.name
  for v in key.data:
   if bun:
    v.co.z-=.136 if '__Hair_Tie' in o.name else .150;v.co.y-=.020
   else:
    t=max(0,min(1,(1.665-v.co.z)/.175));v.co.z-=.112+.018*t;v.co.y+=.008-.025*(1-t)**2
 else:
  cache={}
  for v in key.data:
   p=v.co.copy();d=(p-fit.center).normalized();k=tuple(round(x,3) for x in d)
   hit=cache.get(k)
   if hit is None:
    q=fit.bvh.ray_cast(fit.center,d)[0];hit=q+d*.0009 if q else p;cache[k]=hit
   v.co=hit
 d=key.driver_add('value').driver;v=d.variables.new();v.name='helmet';v.targets[0].id=rig;v.targets[0].data_path='["Wear_Helmet"]';d.expression='1 if helmet else 0'
 o['HelmetFit']='Compressed scalp; long styles exit below the rear rim'

def run(preset):
 name,*_=preset;directory=OUT/name;directory.mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(base.ROOT/'Resources/Models/ProtectorReferenceV2/Chest_Protector_Library.blend'))
 rig=bpy.data.objects['RIG_Body_Medium'];scene=bpy.context.scene
 for o in list(bpy.data.objects):
  if o.type=='MESH' and o.name.startswith('Hair'):bpy.data.objects.remove(o,do_unlink=True)
 warp_all(preset);fit=Hair(bpy.data.objects['Head']);mat=material(rig)
 brow=eyebrows(fit,mat,name.startswith('Male'));bind_eyebrows(brow,bpy.data.objects['Head'])
 rig['HairStyle']=preset[-1];rig['HairColor']=1;rig['Wear_Hair']=True;rig['Wear_Helmet']=False;rig['Wear_Protector']=False;rig['Wear_Gloves']=False;rig['Wear_FootGuards']=False
 rig['CharacterPreset']=name;rig.id_properties_ui('HairStyle').update(min=0,max=5,description='; '.join(f'{i}: {s}' for i,s in enumerate(STYLES)))
 for index,style in enumerate(STYLES):
  coll=bpy.data.collections.new('Hairstyle_'+style);scene.collection.children.link(coll)
  for o in build_hair(fit,index,mat):
   for c in list(o.users_collection):c.objects.unlink(o)
   coll.objects.link(o);o.name='Hair_'+style+'__'+o.name;base.skin(o,rig);helmet_fit(o,fit,rig)
   for attr in ['hide_render','hide_viewport']:
    suite.driver(o,attr,rig,'HairStyle',f'x != {index}');d=o.animation_data.drivers.find(attr).driver;v=d.variables.new();v.name='wear';v.targets[0].id=rig;v.targets[0].data_path='["Wear_Hair"]';d.expression=f'(x != {index}) or not wear'
 rig.update_tag();scene.frame_set(2);scene.frame_set(1);scene.render.resolution_x=1000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
 base.camera(scene,(.43,-1,1.77),(0,-.003,1.57),.52)
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/'Character.blend'),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(directory/'Character.blend'));rig=bpy.data.objects['RIG_Body_Medium'];scene=bpy.context.scene
 scene.render.filepath=str(directory/'Portrait.png');bpy.ops.render.render(write_still=True)
 base.camera(scene,(.75,-2,1.50),(0,0,.91),2.06);scene.render.filepath=str(directory/'Full_Body.png');bpy.ops.render.render(write_still=True)
 if name=='Female_Athletic':
  for index,style in enumerate(STYLES):
   rig['HairStyle']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1);base.camera(scene,(.65,-1,1.82),(0,.025,1.665),.34);scene.render.filepath=str(OUT/(style+'.png'));bpy.ops.render.render(write_still=True)
  rig['HairStyle']=4;rig.update_tag();scene.frame_set(2);scene.frame_set(1);base.camera(scene,(.7,1,1.83),(0,.025,1.66),.36);scene.render.filepath=str(OUT/'Ponytail_Rear.png');bpy.ops.render.render(write_still=True)
 checks={}
 for index,style in enumerate(STYLES):
  rig['HairStyle']=index;rig.update_tag();scene.frame_set(2);scene.frame_set(1);objects=list(bpy.data.collections['Hairstyle_'+style].objects)
  assert all(not o.hide_render for o in objects)
  for o in objects:assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-5 for v in o.data.vertices)
  deps=bpy.context.evaluated_depsgraph_get();o=objects[0];p=(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co).copy();bone=rig.pose.bones['head'];bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((0,0,1),.20);bpy.context.view_layer.update();delta=(o.matrix_world@o.evaluated_get(deps).data.vertices[0].co-p).length;assert delta>.001;bone.rotation_quaternion=Quaternion();bpy.context.view_layer.update()
  checks[style]={'parts':len(objects),'head_attachment_passed':True}
 (directory/'validation.json').write_text(json.dumps({'preset':name,'styles':checks,'body_bones':len(rig.data.bones),'saved_file_reopened':True},indent=2));log('COMPLETE '+name)
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
  for preset in PRESETS:
   if not args or preset[0] in args:run(preset)
 except:log(traceback.format_exc());raise
