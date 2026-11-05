"""Constrain knee contact while retaining live secondary trouser cloth."""
import bpy
from cloth_capsule_contact import capsules

def configure(scene):
 pants=bpy.data.objects.get('Pants')
 rig=next((m.object for m in pants.modifiers if m.type=='ARMATURE' and m.object),None) if pants else None
 if not rig or not pants or 'calf_l' not in rig.data.bones:return False
 cloth=next((m for m in pants.modifiers if m.type=='CLOTH'),None)
 if not cloth:return False
 if pants.get('KneeClothRevision')=='2026-10-30-lower-leg':return False
 scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
 knees=[rig.matrix_world@rig.data.bones['calf_'+side].head_local for side in 'lr']
 points=[pants.matrix_world@v.co for v in pants.data.vertices];top=max(p.z for p in points);bottom=min(p.z for p in points)
 group=pants.vertex_groups.get(cloth.settings.vertex_group_mass)
 if not group:group=pants.vertex_groups.new(name='LiveCloth_Pin')
 cloth.settings.vertex_group_mass=group.name
 for v,p in zip(pants.data.vertices,points):
  knee=min(knees,key=lambda k:abs(k.x-p.x))
  weight=1 if p.z>top-.32*scale or p.z<bottom+.035*scale or abs(p.z-knee.z)<.1*scale else .97
  group.add([v.index],weight,'REPLACE')
 contact=capsules(scene,rig,radius_scale=1.15);contact.name='SIM_Pants_Knee_Contact'
 for o in contact.objects:
  o['PantsContactOnly']=True
  curve=o.driver_add('hide_viewport');driver=curve.driver
  var=driver.variables.new();var.name='enabled';var.targets[0].id=rig;var.targets[0].data_path='["BlenderCloth"]';driver.expression='not enabled'
 cs=cloth.settings;cs.quality=24;cs.pin_stiffness=50;cs.bending_model='ANGULAR';cs.bending_stiffness=15;cs.bending_damping=20
 cs.tension_stiffness=500;cs.compression_stiffness=500;cs.shear_stiffness=200;cs.air_damping=8;cs.use_dynamic_mesh=True
 collision=cloth.collision_settings;collision.collection=contact;collision.use_collision=True;collision.use_self_collision=False;collision.distance_min=.002*scale;collision.collision_quality=8
 pants['KneeClothRevision']='2026-10-30-lower-leg'
 return True

