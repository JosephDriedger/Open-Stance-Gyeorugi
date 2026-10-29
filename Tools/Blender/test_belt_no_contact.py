from pathlib import Path
p=Path(__file__).with_name('refine_belt_render_surface.py');code=p.read_text()
code=code.replace("'Resources/Models/FinalRefinement/BeltSurface'","'Resources/Models/FinalRefinement/BeltNoContact'")
code=code.replace("for p in o.data.polygons:p.use_smooth=True", """for p in o.data.polygons:p.use_smooth=True
 cloth=next(m for m in o.modifiers if m.type=='CLOTH')
 cloth.collision_settings.use_collision=False;cloth.collision_settings.use_self_collision=False""")
exec(compile(code,str(p),'exec'))
