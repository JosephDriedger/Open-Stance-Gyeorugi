"""Verify that hidden source geometry remains available to collision/render readers."""
import bpy,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Resources/Models/FinalRefinement'
bpy.ops.wm.open_mainfile(filepath=str(root/'ClothRefinement_LinearBelt/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];o=bpy.data.objects['Pants'];helper=bpy.data.objects['SIM_Render_Pants']
counts=[]
for hidden in [False,True]:
    o.driver_remove('hide_viewport');o.hide_viewport=hidden;bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get();ev=helper.evaluated_get(deps);me=ev.to_mesh()
    counts.append(len(me.vertices));ev.to_mesh_clear()
assert counts[0]>0 and counts[0]==counts[1],counts
print('HIDDEN_SOURCE_READER_PASS',counts,flush=True)
sys.path.insert(0,str(Path(__file__).parent))
from single_surface_cloth_contact import drive
for prop in ['hide_render','hide_viewport']:
    drive(helper,prop,r,'not live or not pants',True)
    drive(o,prop,r,'live or not pants',True)
states=[]
for live in [False,True]:
    for pants in [False,True]:
        r['BlenderCloth']=live;r['Wear_Pants']=pants;r.update_tag();bpy.context.view_layer.update()
        assert o.hide_viewport==(live or not pants) and o.hide_render==(live or not pants)
        assert helper.hide_viewport==(not live or not pants) and helper.hide_render==(not live or not pants)
        if live and pants:
            ev=helper.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();assert len(me.vertices)>0;ev.to_mesh_clear()
        states.append({'cloth':live,'pants':pants,'source_hidden':o.hide_viewport,'render_helper_hidden':helper.hide_viewport})
(root/'cloth_render_visibility.json').write_text(json.dumps({'helper_vertex_counts':counts,'hidden_source_readable':True,'wardrobe_toggle_states':states},indent=2))
print('CLOTH_WARDROBE_VISIBILITY_PASS',flush=True)
