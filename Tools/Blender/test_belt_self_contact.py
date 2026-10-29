from pathlib import Path
p=Path(__file__).with_name('refine_belt_render_surface.py');code=p.read_text()
code=code.replace("'Resources/Models/FinalRefinement/BeltSurface'","'Resources/Models/FinalRefinement/BeltSelfContact'")
code=code.replace("for p in o.data.polygons:p.use_smooth=True", """for p in o.data.polygons:p.use_smooth=True
 cloth=next(m for m in o.modifiers if m.type=='CLOTH');cs=cloth.settings
 cs.quality=25;cs.mass=.02;cs.use_dynamic_mesh=False;cs.tension_stiffness=500;cs.compression_stiffness=500;cs.shear_stiffness=100;cs.bending_stiffness=100
 cc=cloth.collision_settings;cc.use_self_collision=True;cc.self_distance_min=.0015;cc.self_friction=3;cc.collision_quality=12""")
exec(compile(code,str(p),'exec'))
