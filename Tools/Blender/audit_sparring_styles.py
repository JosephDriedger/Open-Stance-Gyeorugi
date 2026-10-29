"""Read-only sparring wardrobe audit of the installed library."""
import bpy,sys,json,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_fighter_range as audit
import rebuild_updated_characters as build
ROOT=build.ROOT;OUT=ROOT/'Resources/Models/SparringStyleReview_20261016';OUT.mkdir(exist_ok=True)
def load(kind,level):
 source=ROOT/'Resources/Models/CharacterSuite'/kind/(level+'.blend')
 bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
 r.animation_data_create();r.animation_data.action=None
 for t in r.animation_data.nla_tracks:t.mute=True
 for o in s.objects:
  if o.get('MarkerLabel'):o.hide_render=True
 for k in ['Wear_Jacket','Wear_Pants','Wear_Hair','Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[k]=True
 r['BlenderCloth']=False;build.refresh(r)
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;audit.pose(r,'Neutral',scale)
 s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.use_denoising=True;s.render.resolution_percentage=100
 return s,r,scale,source
def render(s,r,scale,d,label,pos,target,ortho,w=480,h=540):
 dest=d/(label+'.png')
 if not dest.exists():
  s.render.resolution_x=w;s.render.resolution_y=h;build.view.camera(s,tuple(x*scale for x in pos),tuple(x*scale for x in target),ortho*scale)
  s.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
 return dest.name
def select(r,j,h,p,color=0,hair=None):
 r['JacketStyle']=j;r['HelmetDesign']=h;r['ProtectorDesign']=p;r['MatchSide']=color
 if hair is not None:r['HairStyle']=hair
 build.refresh(r)
 for names,chosen in [(build.HELMETS,h),(build.PROTECTORS,p)]:
  for i,prefix in enumerate(names):
   objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(prefix+'__')]
   assert objects,(prefix,'missing design')
   assert all(o.hide_render==(i!=chosen) for o in objects),(prefix,'visibility mismatch')
def run(kind,mode):
 d=OUT/kind/mode;d.mkdir(parents=True,exist_ok=True);rows=[]
 if mode=='body':
  s,r,z,src=load(kind,'Gameplay_High')
  for j in range(2):
   for h in range(3):
    for p in range(2):
     select(r,j,h,p,(j+h+p)%2);audit.pose(r,'Neutral',z)
     label=f'J{j}_H{h}_P{p}'
     rows.append(render(s,r,z,d,label+'_Front',(1.7,-4,1.65),(0,0,.96),2.35))
     if j==0:rows.append(render(s,r,z,d,label+'_Rear',(1.8,4,1.65),(0,0,.96),2.35))
  for i,pose in enumerate(['Arms_Overhead','Cross_Body','Knee_L','Deep_Squat']):
   select(r,i%2,i%3,i%2,i%2);audit.pose(r,pose,z)
   rows.append(render(s,r,z,d,'Motion_'+pose,(2,-4,1.65),(0,0,.96),2.35))
 elif mode=='hair':
  s,r,z,src=load(kind,'Preview')
  for h in range(3):
   for style in range(6):
    select(r,0,h,0,h%2,style);audit.pose(r,'Neutral',z)
    active=[o for o in s.objects if o.type=='MESH' and o.name.startswith('Hair_'+build.hair.STYLES[style]+'__')]
    assert active and all(not o.hide_render for o in active)
    assert all(o.data.shape_keys and abs(o.data.shape_keys.key_blocks['HelmetFit'].value-1)<.001 for o in active)
    label=f'H{h}_Hair{style}'
    rows.append(render(s,r,z,d,label+'_Front',(.50,-1,1.84),(0,0,1.66),.46,480,480))
    if style>=3:rows.append(render(s,r,z,d,label+'_Rear',(.50,1,1.84),(0,.02,1.65),.48,480,480))
 elif mode=='lod':
  for i,level in enumerate(['Gameplay_Mid','Gameplay_Far']):
   s,r,z,src=load(kind,level);select(r,i,i+1,i,i);audit.pose(r,'Cross_Body',z)
   rows.append(render(s,r,z,d,level,(1.7,-4,1.65),(0,0,.96),2.35))
 (d/'manifest.json').write_text(json.dumps({'source_last_loaded':str(src),'mode':mode,'renders':rows,'simulation':'Off: default skinning and pose correctives','source_files_saved':False},indent=2))
 with (OUT/(mode+'.log')).open('a') as f:f.write(kind+' COMPLETE\n')
if __name__=='__main__':
 mode=sys.argv[sys.argv.index('--')+1]
 try:
  for kind in build.PRESETS:run(kind,mode)
  with (OUT/(mode+'.log')).open('a') as f:f.write('ALL COMPLETE\n')
 except:(OUT/(mode+'_error.log')).write_text(traceback.format_exc());raise
