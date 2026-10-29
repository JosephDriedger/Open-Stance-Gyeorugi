import bpy,sys,time,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
import repair_sparring_fit as fix
OUT=fix.OUT/'VisualQA';OUT.mkdir(exist_ok=True)
def wait(p):
    deadline=time.monotonic()+7200
    while not p.exists():
        if time.monotonic()>deadline:raise RuntimeError('Waiting for '+str(p))
        time.sleep(5)
try:
    for kind in a.build.PRESETS:
        d=OUT/kind;d.mkdir(exist_ok=True);renders=[]
        for level in ['Gameplay_High','Preview']:
            wait(fix.OUT/kind/(level+'_validation.json'))
            source=fix.OUT/kind/(level+'.blend')
            bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
            assert s.get('SparringFitRepair')=='2026-10-18'
            r.animation_data_create();r.animation_data.action=None
            for t in r.animation_data.nla_tracks:t.mute=True
            for o in s.objects:
                if o.get('MarkerLabel'):o.hide_render=True
            for key in ['Wear_Jacket','Wear_Pants','Wear_Hair','Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[key]=True
            r['BlenderCloth']=False
            z=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
            s.cycles.samples=12;s.render.resolution_percentage=100
            if level=='Gameplay_High':
                for j in range(2):
                    for p in range(2):
                        a.select(r,j,(j+p)%3,p,0);a.audit.pose(r,'Neutral',z)
                        renders.append(a.render(s,r,z,d,f'J{j}_P{p}',(1.7,-4,1.65),(0,0,.96),2.35,640,720))
                for i,pose in enumerate(['Arms_Overhead','Cross_Body','Knee_L','Deep_Squat']):
                    a.select(r,i%2,i%3,i%2,0);a.audit.pose(r,pose,z)
                    renders.append(a.render(s,r,z,d,pose,(1.7,-4,1.65),(0,0,.96),2.35,640,720))
            else:
                a.audit.pose(r,'Neutral',z)
                for h in range(3):
                    for style in [1,3,4,5]:
                        a.select(r,0,h,0,0,style)
                        for side,pos in [('Front',(.5,-1,1.84)),('Rear',(.5,1,1.84))]:
                            renders.append(a.render(s,r,z,d,f'H{h}_Hair{style}_{side}',pos,(0,0,1.65),.55,480,480))
        (d/'manifest.json').write_text(json.dumps({'renders':renders,'source_saved':False},indent=2))
        with (OUT/'review.log').open('a') as f:f.write(kind+' COMPLETE\n')
    with (OUT/'review.log').open('a') as f:f.write('ALL COMPLETE\n')
except:(OUT/'error.log').write_text(traceback.format_exc());raise
