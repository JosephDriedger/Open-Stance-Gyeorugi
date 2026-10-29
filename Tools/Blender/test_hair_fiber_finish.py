"""Stage close-up hair surface review without altering the delivered models."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
import refine_final_hair as hair
projected=sys.argv[-1]=='Projected'
normals=sys.argv[-1]=='Normals'
fine=sys.argv[-1] in ['Fine','Projected','Normals']
out=a.ROOT/'Resources/Models/FinalRefinement'/('HairNormalsReview' if normals else 'HairProjectedFiberReview' if projected else 'HairFineFiberReview' if fine else 'HairFiberReview');out.mkdir(exist_ok=True)
for kind in ['Compact','Medium']:
    s,r,scale,source=a.load(kind,'Gameplay_High')
    hair.pony(s,r);hair.texture_finish(s)
    for material in bpy.data.materials:
        if not material.name.startswith('FiberFinish_') or not material.use_nodes:continue
        for node in material.node_tree.nodes:
            if node.type=='BSDF_PRINCIPLED':
                node.inputs['Roughness'].default_value=.48
                if 'Anisotropic IOR Level' in node.inputs:node.inputs['Anisotropic IOR Level'].default_value=.65
            elif node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.7
    s.cycles.samples=24
    if fine:
        from refine_hair_fiber_surface import apply
        apply(s,r,out)
    if projected or normals:
        from fit_hair_fibers_to_coverage import apply as project, outward_coverage
        if normals:(out/(kind+'_normals.json')).write_text(json.dumps(outward_coverage(s,r),indent=2))
        (out/(kind+'_projection.json')).write_text(json.dumps(project(s),indent=2))
    for style in [3,4]:
        r['HairStyle']=style
        for helmet in [False,True]:
            r['Wear_Helmet']=helmet;a.build.refresh(r)
            a.render(s,r,scale,out,kind+'_'+str(style)+'_'+str(int(helmet)),(.5,1,1.84),(0,0,1.64),.54,600,650)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(kind+'_HairCandidate.blend')),compress=True)
    print('HAIR_CANDIDATE',kind,flush=True)
