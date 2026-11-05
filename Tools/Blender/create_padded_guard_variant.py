import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/FootguardVariantReview';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardCorrectedKickReview/Animation_Test.blend'))
r=bpy.data.objects['RIG_Body_Stocky'];s=bpy.context.scene;s.frame_set(1);scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
o=bpy.data.objects['FootGuards_PaddedInstep'];assert len(o.data.vertices)==12288
axes=[]
for side in 'lr':
 foot=r.matrix_world@r.data.bones['foot_'+side].head_local;ball=r.matrix_world@r.data.bones['ball_'+side].head_local;forward=ball-foot;forward.z=0;length=forward.length;forward.normalize();axes.append((foot,forward,Vector((-forward.y,forward.x,0)),length))
count=0;maximum=0
for v in o.data.vertices:
 if 3072<=v.index<6144 or v.index>=9216:continue
 p=o.matrix_world@v.co;n=(o.matrix_world.to_3x3()@v.normal).normalized();foot,forward,lat,length=min(axes,key=lambda a:abs(p.x-a[0].x));d=p-foot
 along=d.dot(forward)-max(0,d.z)*.85;start=.025*scale;end=length-.013*scale;half=(end-start)/2
 q=(d.dot(lat)/(.043*scale))**2+((along-(start+end)/2)/half)**2
 fade=max(0,1-q)**2;top=max(0,min(1,(n.z-.1)/.55));amount=.008*scale*fade*top
 if amount>1e-7:v.co+=o.matrix_world.inverted().to_3x3()@(n*amount);count+=1;maximum=max(maximum,amount)
o.data.update();r['FootGuardsStyle']=1;r.update_tag();bpy.context.view_layer.update()
assert not o.hide_render and bpy.data.objects['FootGuards'].hide_render
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
(OUT/'variant.json').write_text(json.dumps({'production_installed':False,'modified_object':o.name,'moved_outer_vertices':count,'maximum_padding_m':maximum,'inner_lining_changed':False,'skin_weights_changed':False,'selector':'RIG_Body_Stocky[FootGuardsStyle]: 0 standard, 1 padded'},indent=2))
