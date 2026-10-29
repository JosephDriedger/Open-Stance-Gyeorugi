import bpy,sys,json,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import refine_bun_form as fix
import extend_garment_repairs as base
import rebuild_updated_characters as build
import tailor_doboks as profiles
import audit_sparring_styles as audit
OUT=fix.OUT

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()

def run(kind,level,source):
 d=OUT/kind;d.mkdir(exist_ok=True);check=d/(level+'_validation.json')
 if check.exists():return
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 signature=base.signature(r);actions=base.actions();coords=[tuple(v.co) for v in bpy.data.objects['Body'].data.vertices]
 changes=fix.repair(s);assert signature==base.signature(r) and actions==base.actions() and coords==[tuple(v.co) for v in bpy.data.objects['Body'].data.vertices]
 original={k:r[k] for k in ['HairStyle','Wear_Hair','Wear_Helmet']}
 for gear in [False,True]:
  for style in [0,5]:
   r['Wear_Helmet']=gear;r['Wear_Hair']=True;r['HairStyle']=style;build.refresh(r)
   for name in ['Coiled_Bun_Core','Coiled_Bun','Hair_Tie']:
    o=bpy.data.objects['Hair_Compact_Bun__'+name];assert o.hide_render==(style!=5)
    assert o.data.shape_keys.key_blocks['HelmetFit'].value==int(gear)
    assert all(v.groups and abs(sum(g.weight for g in v.groups)-1)<.001 for v in o.data.vertices)
 for k,v in original.items():r[k]=v
 build.refresh(r);dest=d/source.name;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
 report={'passed':True,'file':dest.name,'source':str(source.relative_to(fix.ROOT)),'sha256':sha(dest),'rig_unchanged':True,'actions_unchanged':True,'body_unchanged':True,'repair':changes}
 check.write_text(json.dumps(report,indent=2))
 if level in ['Preview','Gameplay_High']:
  r.animation_data_create();r.animation_data.action=None
  for tr in r.animation_data.nla_tracks:tr.mute=True
  for o in s.objects:
   if o.get('MarkerLabel'):o.hide_render=True
  z=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;audit.audit.pose(r,'Neutral',z);s.cycles.samples=16;r['HairStyle']=5
  qa=d/'QA';qa.mkdir(exist_ok=True)
  for helmet in [-1,0,1,2]:
   r['Wear_Helmet']=helmet>=0;r['Wear_Protector']=helmet>=0;r['HelmetDesign']=max(0,helmet);build.refresh(r)
   for side,pos in [('Rear',(.45,1,1.8)),('Side',(.9,.35,1.78))]:audit.render(s,r,z,qa,f'{level}_H{helmet}_{side}',pos,(0,.05,1.65),.45,480,480)
 with (OUT/'build.log').open('a') as f:f.write(kind+' '+level+' COMPLETE\n')
try:
 kinds=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else build.PRESETS
 for kind in kinds:
  for level in profiles.LEVELS:run(kind,level,base.source(kind,level))
  run(kind,'Tpose',fix.ROOT/'Resources/Models/TPose'/f'OpenStance_{kind}_Tpose.blend')
 if 'Medium' in kinds:
  for name in ['Medium_Sparring_Samples','Front_Kick']:run('Medium',name,fix.ROOT/'Resources/Models/Animation/Samples'/(name+'.blend'))
except:
 with (OUT/'error.log').open('a') as f:f.write(traceback.format_exc())
 raise
