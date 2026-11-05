import bpy,bmesh,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardSurfaceCollision';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardQuadRebuildV4/Candidate.blend'))
s=bpy.context.scene;body=bpy.data.objects['Body'];target=body.copy();target.data=body.data.copy();s.collection.objects.link(target);target.name='Guard_FullBody_Collision';target.hide_render=True;target['SimulationOnly']=True
for m in list(target.modifiers):
 if m.type=='MASK':target.modifiers.remove(m)
for name in ('FootGuards','FootGuards_PaddedInstep'):
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
 doomed=[v for v in bm.verts if 3072<=v.index<6144 or v.index>=9216]
 bmesh.ops.delete(bm,geom=doomed,context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update()
 fit=o.modifiers.new('Animated_body_clearance','SHRINKWRAP');fit.target=target;fit.wrap_method='NEAREST_SURFACEPOINT';fit.wrap_mode='OUTSIDE';fit.offset=.002
 lining=o.modifiers.new('Regenerated_lining','SOLIDIFY');lining.thickness=.001;lining.offset=-1;lining.use_even_offset=True
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'setup.json').write_text(json.dumps({'production_installed':False,'scope':'Blender post-skinning surface constraint and generated lining; not a cloth simulation or verified game export'},indent=2))
