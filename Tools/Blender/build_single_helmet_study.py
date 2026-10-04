"""One review helmet: open crown, shaped brow/cheek band, rounded ear pads.
Does not replace the character suite. Run headless Blender.
"""
import bpy,bmesh,math,json,sys,traceback
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/HelmetStudy';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_reference_helmets as util
import build_character_suite as suite
LOG=OUT/'build.log'
def log(s):
 with LOG.open('a') as f:f.write(str(s)+'\n')
def interpolate(z,values):
 for (a,x),(b,y) in zip(values,values[1:]):
  if a<=z<=b:
   t=(z-a)/(b-a);return x+(y-x)*t
 return values[0][1] if z<values[0][0] else values[-1][1]
def skin(o,rig):
 o.vertex_groups.clear();o.vertex_groups.new(name='head').add(list(range(len(o.data.vertices))),1,'REPLACE');suite.bind(o,rig)
def smooth_surface(o,thickness=.014,subdivision=2):
 # Weld the front seam of the closed brow rings before subdivision.
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 m=o.modifiers.new('Curved foam surface','SUBSURF');m.levels=subdivision;util.apply(o,m)
 m=o.modifiers.new('Actual padding thickness','SOLIDIFY');m.thickness=thickness;m.offset=0;util.apply(o,m)
 util.bevel(o,.0035,4)
 for p in o.data.polygons:p.use_smooth=True
 return o
def padded_strip(name,centers,widths,mat):
 verts=[];faces=[];cols=8
 for i,(point,width) in enumerate(zip(centers,widths)):
  for j in range(cols+1):
   u=2*j/cols-1
   # Follow the scalp across the wider cap instead of making a flat roof.
   dome=math.sin(math.pi*i/(len(centers)-1))
   verts.append((point[0]+u*width/2,point[1],point[2]+.0018-.009*dome*u*u))
 for i in range(len(centers)-1):
  for j in range(cols):a=i*(cols+1)+j;faces.append((a,a+1,a+cols+2,a+cols+1))
 return smooth_surface(util.mesh(name,verts,faces,mat),.014)
def band(mat,vents=True):
 zs=[1.523,1.526,1.537,1.552,1.572,1.593,1.615,1.637,1.655,1.668,1.676,1.682,1.686,1.700,1.718,1.721]
 aperture=[(1.523,.72),(1.552,.82),(1.593,1.05),(1.637,1.02),(1.668,.82),(1.676,.67),(1.682,.33),(1.686,0),(1.721,0)]
 verts=[];faces=[];segments=100
 for z in zs:
  start=interpolate(z,aperture)
  for i in range(segments+1):
   theta=start+(math.tau-2*start)*i/segments
   # The jaw rises toward the rear of the helmet, clearing the neck.
   lift=.033*max(0,min(1,(z-1.590)/(-.067)))*(math.sin(theta/2)**.6)
   rise=(.026*math.sin(theta)**2+.011*max(0,-math.cos(theta)))*max(0,(z-1.640)/.081)**2
   dz=z+lift+rise
   rx=interpolate(dz,[(1.52,.085),(1.57,.093),(1.64,.095),(1.69,.094),(1.73,.087)])
   ry=interpolate(dz,[(1.52,.105),(1.58,.111),(1.66,.119),(1.73,.112)])
   verts.append((rx*math.sin(theta),-.009-ry*math.cos(theta),dz))
 for row in range(len(zs)-1):
  for j in range(segments):a=row*(segments+1)+j;faces.append((a,a+1,a+segments+2,a+segments+1))
 o=smooth_surface(util.mesh('Foam_Brow_Cheeks_Occipital',verts,faces,mat))
 # Small, correctly scaled vents through the side panel, not a perforated dome.
 if vents:
  for y,z,r in [(-.046,1.669,.0085),(-.019,1.654,.007),(.013,1.668,.008),(.044,1.655,.008),(.066,1.619,.008),(.042,1.579,.0065)]:util.hole(o,(0,y,z),(r,r),'X')
 util.hole(o,(0,-.006,1.616),(.016,.027),'X')
 util.bevel(o,.0014,3)
 for p in o.data.polygons:p.use_smooth=True
 return o
def crown(mat):
 # User's supplied front/rear photographs show a broad padded crown cap.
 # Keep the paired front openings, but reduce their exposed scalp area.
 centers=[];width=[]
 for i in range(25):
  t=i/24;y=-.115+.215*t;z=1.719+.046*(math.sin(math.pi*t)**.8)
  centers.append((0,y,z));width.append(.070+.035*math.sin(math.pi*t)**.8)
 bridge=padded_strip('Foam_Crown_Bridge',centers,width,mat)
 # Back upper pad closes the rear crown, while leaving two large front openings.
 verts=[];faces=[];cols=32;rows=12
 for r in range(rows+1):
  t=r/rows
  for c in range(cols+1):
   a=-math.pi/2+math.pi*c/cols
   x=.087*math.sin(a)*(1-t);y=.011+.092*math.cos(a)*(1-t);base=1.732+.015*abs(math.sin(a));z=base+(1.765-base)*math.sin(t*math.pi/2)
   verts.append((x,y,z))
 for r in range(rows):
  for c in range(cols):i=r*(cols+1)+c;faces.append((i,i+1,i+cols+2,i+cols+1))
 rear=smooth_surface(util.mesh('Foam_Rear_Crown',verts,faces,mat))
 return [bridge,rear]
def ear_pad(sign,mat):
 # Smooth toroidal cross-section with a narrow-waisted ear opening.
 verts=[];faces=[];n=96;cross=32
 for i in range(n):
  a=math.tau*i/n
  for j in range(cross):
   p=math.tau*j/cross;t=(1+math.copysign(abs(math.cos(p))**.35,math.cos(p)))/2
   ry=.013+(.035-.013)*t;rz=.027+(.044-.027)*t
   pinch=1-.3*math.exp(-(math.sin(a)/.3)**2)*(1-t)
   verts.append((sign*(.101+.005*math.copysign(abs(math.sin(p))**.35,math.sin(p))),-.006+ry*math.cos(a)*pinch,1.615+rz*math.sin(a)))
 for i in range(n):
  for j in range(cross):faces.append((i*cross+j,((i+1)%n)*cross+j,((i+1)%n)*cross+(j+1)%cross,i*cross+(j+1)%cross))
 return util.mesh('Foam_Ear_'+('L' if sign==1 else 'R'),verts,faces,mat)
def strap(mat):
 points=[]
 for i in range(41):
  t=i/40;x=-.085+.170*t
  points.append((x,-.097+.038*(abs(x)/.085)**2,1.516+.044*(abs(x)/.085)**1.8))
 return util.ribbon('Woven_Chin_Strap',points,.019,mat)
def patches(mat):
 pieces=[]
 for sign in [-1,1]:
  verts=[];faces=[]
  for row in range(5):
   z=1.552+.028*row/4;rx=interpolate(z,[(1.52,.085),(1.57,.093)]);ry=interpolate(z,[(1.52,.105),(1.58,.111)])
   for col in range(5):
    a=1.05+.25*col/4;verts.append((sign*(rx+.010)*math.sin(a),-.009-(ry+.010)*math.cos(a),z))
  for row in range(4):
   for col in range(4):i=row*5+col;faces.append((i,i+1,i+6,i+5))
  o=util.mesh('Chin_Strap_Fastener',verts,faces,mat);m=o.modifiers.new('Fastener backing','SOLIDIFY');m.thickness=.0015;util.apply(o,m);util.bevel(o,.001,3);pieces.append(o)
 return pieces
def camera(scene,position,target,scale):
 c=scene.camera;c.location=position;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=scale
def run():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/CharacterSuite/Medium/Preview.blend'))
 rig=bpy.data.objects['RIG_Body_Medium']
 for o in list(bpy.data.objects):
  if o.type=='MESH' and o.name.startswith('Helmet'):bpy.data.objects.remove(o,do_unlink=True)
 rig['MatchSide']=1;rig['Wear_Hair']=False;rig.update_tag();bpy.context.scene.frame_set(2);bpy.context.scene.frame_set(1)
 foam=util.material('Study_Dipped_Red_Foam',rig,.31);web=util.material('Study_Black_Webbing',rig,.86,False)
 bs=foam.node_tree.nodes.get('Principled BSDF');bs.inputs['Coat Weight'].default_value=.18
 shell=band(foam);crown_parts=crown(foam)
 construction=bpy.data.collections.new('Construction_Crown_Parts');scene=bpy.context.scene;scene.collection.children.link(construction)
 for part in crown_parts:
  m=shell.modifiers.new('Molded crown connection','BOOLEAN');m.operation='UNION';m.solver='EXACT';m.object=part;util.apply(shell,m)
  for c in list(part.users_collection):c.objects.unlink(part)
  construction.objects.link(part);part.hide_render=True;part.hide_set(True)
 shell.name='Molded_Foam_Shell'
 # One small through-vent in the crown, like the supplied elevated/rear view.
 util.hole(shell,(0,.026,1.79),(.0105,.0105),'Z');util.bevel(shell,.0012,3)
 # Blend construction joins into one continuous molded foam surface.
 m=shell.modifiers.new('Continuous molded foam','REMESH');m.mode='VOXEL';m.voxel_size=.0012;m.use_smooth_shade=True;util.apply(shell,m)
 m=shell.modifiers.new('Rounded foam joins','SMOOTH');m.factor=.8;m.iterations=5;util.apply(shell,m)
 m=shell.modifiers.new('Foam surface finish','SUBSURF');m.levels=1;util.apply(shell,m)
 for p in shell.data.polygons:p.use_smooth=True
 pieces=[shell]+[ear_pad(s,foam) for s in [-1,1]]+[strap(web)]+patches(web)
 coll=bpy.data.collections.new('HELMET_STUDY_Editable_Parts');bpy.context.scene.collection.children.link(coll)
 for o in pieces:
  for c in list(o.users_collection):c.objects.unlink(o)
  coll.objects.link(o);skin(o,rig);o['Reference']='https://us.adidascombatsports.com/products/adidas-head-guard'
 scene=bpy.context.scene;scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
 if scene.render.engine=='CYCLES':scene.cycles.samples=48
 target=(0,-.007,1.65);camera(scene,(.62,-1,1.82),target,.39)
 bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Single_Helmet_Review.blend'),compress=True)
 for name,pos in [('Front',(0,-1,1.68)),('Side',(1,-.007,1.68)),('ThreeQuarter',(.62,-1,1.82))]:
  camera(scene,pos,target,.39);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
 # Product view separates the helmet silhouette from the character's appearance.
 for o in scene.objects:
  if o.type=='MESH' and o not in pieces:
   if o.animation_data:
    for d in o.animation_data.drivers:
     if d.data_path=='hide_render':d.mute=True
   o.hide_render=True
 camera(scene,(.65,-1,1.90),target,.37);scene.render.filepath=str(OUT/'Helmet_Only.png');bpy.ops.render.render(write_still=True)
 camera(scene,(.45,-.65,2.30),(0,-.007,1.67),.35);scene.render.filepath=str(OUT/'Crown_Elevated.png');bpy.ops.render.render(write_still=True)
 report={'scope':'Single helmet study, no suite rollout','revision':'Broader 70–105 mm crown cap with small round top vent, based on four user-supplied reference photos','parts':{},'reference':'https://us.adidascombatsports.com/products/adidas-head-guard'}
 for o in pieces:o.data.calc_loop_triangles();report['parts'][o.name]=len(o.data.loop_triangles)
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2));log('COMPLETE')
if __name__=='__main__':
 try:run()
 except:log(traceback.format_exc());raise
