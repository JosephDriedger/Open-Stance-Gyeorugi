from pathlib import Path
p=Path(__file__).with_name('test_final_cloth_contact.py')
s=p.read_text().replace("('ClothFinal_'+str(style))","('ClothSettle_'+str(style))")
s=s.replace('baselines={};rows=[]',"""for collider in belt_contact.objects:
 if collider.type=='MESH' and collider.data.shape_keys:
  keys=collider.data.shape_keys
  if keys.animation_data:keys.animation_data.action=None
  for k in keys.key_blocks:
   if k.name.startswith(('ClothBake','Pose_')):k.value=0
baselines={};rows=[]""")
s=s.replace('m.collision_settings.collection=belt_contact',"if name.startswith('Belt_Tail'):cs.bending_stiffness=50;cs.mass=.03;cs.quality=20;cs.bending_damping=10;cs.air_damping=8\n   m.collision_settings.collection=belt_contact")
s=s.replace('frame_end=72','frame_end=144').replace('range(1,73)','range(1,145)').replace('[1,26,35,72]','[1,26,35,72,120,144]')
s=s.replace("with (out/'progress.log').open('a')", "if frame in [72,144]:a.render(s,r,1,out,'Front_'+str(frame),(.2,-4,1.3),(0,0,.96),1.25,640,720)\n with (out/'progress.log').open('a')")
exec(compile(s,str(p),'exec'))
