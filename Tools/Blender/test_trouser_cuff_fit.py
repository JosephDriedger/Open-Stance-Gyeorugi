import bpy,sys
from pathlib import Path
from mathutils import Vector
p=bpy.data.objects['Pants']; rig=bpy.data.objects['RIG_Body_Stocky']; cloth=next(m for m in p.modifiers if m.type=='CLOTH')
group=p.vertex_groups[cloth.settings.vertex_group_mass]
for side in ('l','r'):
 ankle=rig.matrix_world@rig.data.bones['foot_'+side].head_local
 knee=rig.matrix_world@rig.data.bones['calf_'+side].head_local
 axis=(knee-ankle).normalized()
 verts=[v for v in p.data.vertices if (p.matrix_world@v.co).x*ankle.x>0]
 low=min(((p.matrix_world@v.co)-ankle).dot(axis) for v in verts)
 for v in verts:
  pos=p.matrix_world@v.co; h=(pos-ankle).dot(axis); t=h-low
  if t>.15:continue
  influence=max(0,min(1,(.15-t)/.08));influence=influence**2*(3-2*influence)
  radial=pos-ankle-axis*h
  v.co=p.matrix_world.inverted()@(pos+radial.normalized()*.009*influence)
  group.add([v.index],influence,'REPLACE')
out=Path(bpy.path.abspath('//')).parent/'TrouserCuffFit';out.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Trouser_Test.blend'),compress=True)
sys.path.insert(0,str(Path.cwd()/'Tools/Blender'));import audit_sparring_styles as review
s=bpy.context.scene;scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
for frame in range(1,s.frame_end+1):
 s.frame_set(frame);bpy.context.evaluated_depsgraph_get().update()
 if frame in (30,86,95,110,144,s.frame_end):review.render(s,rig,scale,out,'Review_'+str(frame),(4,-.8,1.65),(0,-.25,.95),2.25,480,600)
