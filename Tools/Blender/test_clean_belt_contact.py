from pathlib import Path
p=Path(__file__).with_name('test_final_cloth_contact.py')
s=p.read_text().replace("('ClothFinal_'+str(style))","('ClothCleanContact_'+str(style))")
s=s.replace('baselines={};rows=[]',"""for collider in belt_contact.objects:
 if collider.type=='MESH' and collider.data.shape_keys:
  keys=collider.data.shape_keys
  if keys.animation_data:keys.animation_data.action=None
  for k in keys.key_blocks:
   if k.name.startswith(('ClothBake','Pose_')):k.value=0
baselines={};rows=[]""")
s=s.replace('m.collision_settings.collection=belt_contact',"if name.startswith('Belt_Tail'):cs.bending_stiffness=50;cs.mass=.03;cs.quality=20;cs.bending_damping=10;cs.air_damping=8\n   m.collision_settings.collection=belt_contact")
exec(compile(s,str(p),'exec'))
