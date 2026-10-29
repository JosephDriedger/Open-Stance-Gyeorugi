from pathlib import Path
p=Path(__file__).with_name('refine_belt_render_surface.py');code=p.read_text()
code=code.replace("'Resources/Models/FinalRefinement/BeltSurface'","'Resources/Models/FinalRefinement/BeltSoftBody'")
code=code.replace("for p in o.data.polygons:p.use_smooth=True", """for p in o.data.polygons:p.use_smooth=True
 old=next(m for m in o.modifiers if m.type=='CLOTH');contact=old.collision_settings.collection;o.modifiers.remove(old)
 soft=o.modifiers.new('Physical woven belt','SOFT_BODY');cs=o.soft_body
 cs.use_goal=True;cs.vertex_group_goal='LiveCloth_Pin';cs.goal_default=0;cs.goal_min=0;cs.goal_max=1;cs.goal_spring=.9;cs.goal_friction=10
 cs.use_edges=True;cs.use_stiff_quads=True;cs.pull=.95;cs.push=.95;cs.damping=15;cs.bend=10;cs.mass=.01;cs.friction=10
 cs.step_min=10;cs.step_max=100;cs.use_auto_step=True;cs.collision_collection=contact;cs.use_edge_collision=True;cs.use_face_collision=True
 soft.point_cache.frame_start=1;soft.point_cache.frame_end=144
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_move_to_index(modifier=soft.name,index=1)""")
exec(compile(code,str(p),'exec'))
