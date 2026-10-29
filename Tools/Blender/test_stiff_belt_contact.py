from pathlib import Path
p=Path(__file__).with_name('test_final_cloth_contact.py')
s=p.read_text().replace("('ClothFinal_'+str(style))","('ClothStiffBelt_'+str(style))")
s=s.replace('m.collision_settings.collection=belt_contact',"if name.startswith('Belt_Tail'):cs.bending_stiffness=30;cs.mass=.03;cs.quality=20;cs.bending_damping=10;cs.air_damping=8\n   m.collision_settings.collection=belt_contact")
exec(compile(s,str(p),'exec'))
