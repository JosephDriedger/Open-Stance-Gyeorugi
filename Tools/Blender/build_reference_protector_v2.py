"""Revised hogu silhouette from the three user-supplied reference photos."""
import bpy,math,json,sys,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import build_protector_study as old
import build_single_helmet_study as base
import rebuild_reference_helmets as u
OUT=base.ROOT/'Resources/Models/ProtectorReferenceV2';OUT.mkdir(exist_ok=True)

def surface(a,t,offset=0,quilt=False):
 # Front apron drops below the rib wings; upper chest stays nearly straight.
 low=1.080-.125*math.exp(-(abs(a)/.62)**4)
 cut=1/(1+math.exp(-(abs(a)-.80)*18))
 high=1.437-.130*cut+.034*max(0,-math.cos(a))
 z=low+(high-low)*t
 rx=base.interpolate(z,[(.98,.179),(1.08,.210),(1.20,.220),(1.33,.225),(1.44,.215)])
 ry=base.interpolate(z,[(.98,.181),(1.10,.191),(1.26,.194),(1.44,.173)])
 # Extend 30 mm over the knot and flare forward to clear its measured front.
 flare=max(0,min(1,(1.10-z)/.10));flare=flare*flare*(3-2*flare)
 ry+=.076*flare*math.exp(-(abs(a)/.55)**4)
 groove=sum(.0011*math.exp(-((z-q)/.0035)**2) for q in [1.055,1.175,1.295]) if quilt else 0
 return Vector(((rx+offset-groove)*math.sin(a),-.006-(ry+offset-groove)*math.cos(a),z))

def yoke_point(a,t):
 # Broad continuous shoulder yoke surrounding an actual oval neck opening.
 front=max(0,math.cos(a));side=math.sin(a)**2;rear=max(0,-math.cos(a))
 angle=abs(math.atan2(math.sin(a),math.cos(a)))
 def ease(x):
  x=max(0,min(1,x));return x*x*(3-2*x)
 lift=ease((angle-.65)/.60)*ease((math.pi-angle-.38)/.62)
 # Share the chest-panel boundary at front/back; only the arm openings lift.
 joined=surface(a,1);shoulder=Vector((.164*math.sin(a),-.006-.173*math.cos(a),1.492))
 outer=joined.lerp(shoulder,lift)
 inner=Vector((.075*math.sin(a),-.006-.080*math.cos(a),1.495+.010*side))
 p=outer.lerp(inner,t);p.z+=.007*math.sin(math.pi*t)
 return p

def yoke(mat):
 n=144;rows=12;vs=[];fs=[]
 for j in range(rows+1):
  for i in range(n):vs.append(yoke_point(math.tau*i/n,j/rows))
 for j in range(rows):
  for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 return base.smooth_surface(u.mesh('Continuous_White_Shoulder_Yoke',vs,fs,mat),.011,1)

def build(rig,style):
 parts=original_build(rig,style)
 for o in list(parts):
  if o.name.startswith(('Padded_Shoulder_Strap','Shoulder_Seam')):parts.remove(o);bpy.data.objects.remove(o,do_unlink=True)
 white=old.plain('V2_White_Yoke',(.80,.79,.75),.56)
 thread=old.plain('V2_Tonal_Blue_Stitch',(.018,.052,.11),.76)
 parts.append(yoke(white))
 parts.append(u.tube('Bound_Neck_Opening',[yoke_point(math.tau*i/144,1) for i in range(145)],.0034,white))
 # Horizontal stitched rows and the long V-shaped paired seam from references.
 stitch_verts=[];stitch_faces=[]
 def seam(points):
  for i in range(0,len(points)-1,2):
   a,b=Vector(points[i]),Vector(points[i+1]);axis=(b-a).normalized();n=axis.cross(Vector((0,0,1)))
   if n.length<.01:n=axis.cross(Vector((1,0,0)))
   n.normalize();v=axis.cross(n);start=len(stitch_verts)
   for p in [a,b]:
    for j in range(6):stitch_verts.append(p+.00055*(n*math.cos(math.tau*j/6)+v*math.sin(math.tau*j/6)))
   for j in range(6):stitch_faces.append((start+j,start+(j+1)%6,start+6+(j+1)%6,start+6+j))
 for z in [1.055,1.175,1.295]:
  pts=[]
  for i in range(401):
   a=-2.63+5.26*i/400;lo=surface(a,0).z;hi=surface(a,1).z
   if lo+.012<z<hi-.012:pts.append(surface(a,(z-lo)/(hi-lo),.012,True))
  # Bottom row exists only on the apron; avoid connecting separate wings.
  if pts:seam(pts)
 for sign in [-1,1]:
  for shift in [-.010,.010]:
   pts=[]
   for i in range(151):
    t=i/150;a=sign*(.025+.64*t)+shift;z=1.065+.355*t;lo=surface(a,0).z;hi=surface(a,1).z
    if z<hi-.006:pts.append(surface(a,(z-lo)/(hi-lo),.012,True))
   seam(pts)
 if stitch_verts:parts.append(u.mesh('Horizontal_And_V_Panel_Stitching',stitch_verts,stitch_faces,thread))
 return parts

original_build=old.build
old.surface=surface;old.build=build;old.OUT=OUT
old.REFERENCE='User-provided chest protector photographs, October 4, 2026; unbranded interpretation'
if __name__=='__main__':
 try:
  old.run()
  # Isolated view makes the yoke, armholes and apron easy to compare to photos.
  bpy.ops.wm.open_mainfile(filepath=str(OUT/'Chest_Protector_Library.blend'))
  scene=bpy.context.scene;rig=bpy.data.objects['RIG_Body_Medium'];rig['ProtectorDesign']=0;rig['MatchSide']=1;rig.update_tag();scene.frame_set(2);scene.frame_set(1)
  parts=list(bpy.data.collections['Protector_Quilted_Lace_Back'].objects)
  for o in scene.objects:
   if o.type=='MESH' and o not in parts:
    if o.animation_data:
     for d in o.animation_data.drivers:
      if d.data_path=='hide_render':d.mute=True
    o.hide_render=True
  base.camera(scene,(.7,-1.8,1.65),(0,0,1.25),.70);scene.render.filepath=str(OUT/'Reference_Shape_Detail.png');bpy.ops.render.render(write_still=True)
  (OUT/'build.log').write_text('COMPLETE')
 except:(OUT/'build.log').write_text(traceback.format_exc());raise
