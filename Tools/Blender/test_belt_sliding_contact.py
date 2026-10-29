from pathlib import Path
p=Path(__file__).with_name('refine_belt_render_surface.py');code=p.read_text()
code=code.replace("'Resources/Models/FinalRefinement/BeltSurface'","'Resources/Models/FinalRefinement/BeltSlidingContact'")
code=code.replace("for name in ['Belt_Tail_Left','Belt_Tail_Right']:\n o=", """for collider in bpy.data.collections['Cloth_Belt_Contact'].objects:
 collider.hide_render=False
 for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(collider,prop,False)
 collider.collision.cloth_friction=0
for name in ['Belt_Tail_Left','Belt_Tail_Right']:
 o=""",1)
code=code.replace("for p in o.data.polygons:p.use_smooth=True", """for p in o.data.polygons:p.use_smooth=True
 cloth=next(m for m in o.modifiers if m.type=='CLOTH');cloth.settings.quality=30
 cloth.collision_settings.collision_quality=12""")
exec(compile(code,str(p),'exec'))
