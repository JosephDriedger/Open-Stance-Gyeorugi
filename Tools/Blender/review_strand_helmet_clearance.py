import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/StrandGeometryReview'
bpy.ops.wm.open_mainfile(filepath=str(out/'Preview_Bob.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
o=bpy.data.objects['Hair_Chin_Length_Bob__Preview_Strands'];fit=o.data.shape_keys.key_blocks['HelmetFit']
group=o.vertex_groups.new(name='Helmet_Exposed_Strands');group.add([i for i,p in enumerate(fit.data) if p.co.z<1.545*scale],1,'REPLACE')
mask=o.modifiers.new('Hide strands covered by helmet','MASK');mask.vertex_group=group.name
for prop in ['show_viewport','show_render']:
    driver=mask.driver_add(prop).driver;v=driver.variables.new();v.name='helmet';v.targets[0].id=r;v.targets[0].data_path='["Wear_Helmet"]';driver.expression='helmet'
for helmet in [False,True]:
    r['Wear_Helmet']=helmet;a.build.refresh(r)
    a.render(s,r,scale,out,'Fitted_Rear_'+str(int(helmet)),(.5,1,1.84),(0,0,1.64),.54,600,650)
    a.render(s,r,scale,out,'Fitted_Front_'+str(int(helmet)),(.5,-1,1.84),(0,0,1.64),.54,600,650)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'Preview_Bob_HelmetFitted.blend'),compress=True)
