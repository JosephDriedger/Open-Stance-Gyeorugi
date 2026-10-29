"""Ensure physical clearance never changes cloth-off belt authoring geometry."""
import bpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from shared_belt_simulation import configure
import extend_garment_repairs as base
root=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/Animation/Physics/SecondaryCloth_Kick_Study.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];s.frame_set(1)
r['BlenderCloth']=False;r.update_tag();bpy.context.view_layer.update()
names=['Belt_Tail_Left','Belt_Tail_Right']
def geometry():
    result={}
    for name in names:
        o=bpy.data.objects[name]
        result[name]={'vertices':[list(v.co) for v in o.data.vertices],
                      'keys':{k.name:[list(v.co) for v in k.data] for k in o.data.shape_keys.key_blocks} if o.data.shape_keys else {},
                      'matrix':[list(row) for row in o.matrix_world]}
    return result
before=geometry();rig=base.signature(r);actions=base.actions()
configure(s,r);bpy.context.view_layer.update()
assert geometry()==before,'Authoring vertices or shape keys changed'
assert base.signature(r)==rig and base.actions()==actions,'Rig or actions changed'
for name in names:
    output=bpy.data.objects[name].modifiers['Shared physical belt output']
    assert not output.show_render and not output.show_viewport
report={'source_geometry_shape_keys_and_transforms_preserved':True,'rig_actions_preserved':True,'cloth_off_original_geometry':True,'production_files_modified':False}
(root/'Resources/Models/FinalRefinement/shared_belt_preservation.json').write_text(json.dumps(report,indent=2))
print('SHARED_BELT_PRESERVATION_PASS',flush=True)
