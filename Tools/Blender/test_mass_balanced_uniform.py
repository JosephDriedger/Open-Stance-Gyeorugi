"""Test stiffness/damping ratios alongside low per-vertex garment mass."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
contact_test='--contact' in sys.argv
normalized='--normalize' in sys.argv
OUT=review.ROOT/'Resources/Models/FinalRefinement'/('UniformNormalizedContact' if normalized else 'UniformContactThickness' if contact_test else 'UniformMassBalanced');OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(review.ROOT/'Resources/Models/FinalRefinement/FreeUniformCoupled/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
rows=[]
if contact_test:
    for obj in s.objects:
        if any(m.type=='COLLISION' for m in obj.modifiers):
            if normalized:
                from rebuild_belt_solver_mesh import normalize_world_mesh
                normalize_world_mesh(obj)
            obj.collision.thickness_inner=.001*scale;obj.collision.thickness_outer=.002*scale
            obj.collision.use_normal=True;obj.collision.use_culling=False
for obj in s.objects:
    for mod in obj.modifiers:
        if mod.type!='CLOTH':continue
        c=mod.settings;ratio=1 if contact_test else c.mass/.01
        for prop in ('tension_stiffness','compression_stiffness','shear_stiffness','bending_stiffness','tension_damping','compression_damping','shear_damping','bending_damping','air_damping'):
            setattr(c,prop,getattr(c,prop)*ratio)
        rows.append(dict(object=obj.name,vertex_mass=c.mass,coefficient_scale=ratio))
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
for frame in range(1,31):
    s.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
    for row in rows:
        ev=bpy.data.objects[row['object']].evaluated_get(dg);mesh=ev.to_mesh();ev.to_mesh_clear()
    print('BALANCED_FRAME',frame,flush=True)
review.render(s,r,scale,OUT,'Rest_30',(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
(OUT/'report.json').write_text(json.dumps(dict(production_installed=False,frames=30,settings=rows,scope='Stationary numerical-conditioning trial; no calibrated real-material or animation acceptance'),indent=2))
