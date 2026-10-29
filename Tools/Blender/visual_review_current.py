"""Render installed files without saving or changing them."""
import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_fighter_range as audit
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/VisualReview_20261016';OUT.mkdir(exist_ok=True)
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
def run(kind):
 source=ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 r.animation_data_create();r.animation_data.action=None
 for t in r.animation_data.nla_tracks:t.mute=True
 for o in s.objects:
  if o.get('MarkerLabel'):o.hide_render=True
 r['BlenderCloth']=False
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 s.render.engine='CYCLES';s.cycles.samples=8;s.render.resolution_x=560;s.render.resolution_y=630;s.render.resolution_percentage=100
 d=OUT/kind;d.mkdir(exist_ok=True);rows=[]
 views=[('Front',(0,-4,1.5)),('Back',(0,4,1.5)),('Side',(4,0,1.5))]
 for gear in [False,True]:
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
  r['JacketStyle']=int(gear);audit.build.refresh(r)
  for pose in ['Neutral','Arms_Overhead','Knee_L','Front_Kick_L','Deep_Squat']:
   audit.pose(r,pose,scale)
   for view,pos in (views if pose=='Neutral' else [('ThreeQuarter',(2,-4,1.7))]):
    label=f'{int(gear)}_{pose}_{view}';dest=d/(label+'.png')
    audit.build.view.camera(s,tuple(v*scale for v in pos),(0,0,.96*scale),2.35*scale)
    if not dest.exists():s.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
    rows.append({'file':dest.name,'pose':pose,'gear':gear,'jacket_style':int(gear)})
 (d/'render_manifest.json').write_text(json.dumps({'source':str(source),'renders':rows,'live_cloth':False},indent=2))
 with (OUT/'render.log').open('a') as f:f.write(kind+' COMPLETE\n')
try:
 args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else KINDS
 for kind in args:run(kind)
except:
 (OUT/'error.log').write_text(traceback.format_exc());raise
