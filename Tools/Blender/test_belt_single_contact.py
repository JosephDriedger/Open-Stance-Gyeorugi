from pathlib import Path
p=Path(__file__).with_name('refine_belt_render_surface.py');code=p.read_text()
code=code.replace("'Resources/Models/FinalRefinement/BeltSurface'","'Resources/Models/FinalRefinement/BeltSingleContact'")
code=code.replace("for name in ['Belt_Tail_Left','Belt_Tail_Right']:\n o=", """outer=bpy.data.collections.new('SIM_Belt_Single_Garment');s.collection.children.link(outer)
source=bpy.data.objects['SIM_Pants_Collider'];proxy=source.copy();proxy.data=source.data.copy();proxy.name='SIM_Belt_Single_Garment';outer.objects.link(proxy)
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
inverse=proxy.matrix_world.inverted().to_3x3();normal_matrix=proxy.matrix_world.to_3x3().inverted().transposed()
for v in proxy.data.vertices:
 z=(proxy.matrix_world@v.co).z/scale;amount=(.008+.027*max(0,min(1,(z-.65)/.15)))*scale
 delta=inverse@((normal_matrix@v.normal).normalized()*amount)
 v.co+=delta
 if proxy.data.shape_keys:
  for key in proxy.data.shape_keys.key_blocks:key.data[v.index].co+=delta
proxy.hide_render=False;proxy.collision.cloth_friction=0
for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(proxy,prop,False)
for name in ['Belt_Tail_Left','Belt_Tail_Right']:
 o=""",1)
code=code.replace("for p in o.data.polygons:p.use_smooth=True", """for p in o.data.polygons:p.use_smooth=True
 cloth=next(m for m in o.modifiers if m.type=='CLOTH');cloth.settings.quality=30
 cloth.collision_settings.collection=outer;cloth.collision_settings.collision_quality=12""")
exec(compile(code,str(p),'exec'))
