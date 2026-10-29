from pathlib import Path
import json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';S=M/'ExportMaterialRepair';C=M/'CrowdFaceRefinement'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def check(p,count):
 r=read(p);assert r['passed'] and len(r['files'])==count,p
 for row in r['files']:assert sha(p.parent/row['file'])==row['sha256'],row['file']
 return r
mb=check(S/'motionbuilder_validation.json',36);mapping=[]
def add(src,dst):assert src.is_file(),src;mapping.append((src,dst))
for kind in KINDS:
 for level in ['Crowd_Near','Crowd_Far']:
  r=read(C/kind/(level+'_validation.json'));src=C/kind/(level+'.blend');dst=M/'CharacterSuite'/kind/src.name
  assert r['passed'] and r['rig_and_actions_preserved'] and r['ponytail_root_attached'] and sha(src)==r['sha256'] and sha(dst)==r['source_sha256']
  add(src,dst)
  for style in [0,1]:
   counts=read(C/kind/(level+'_'+str(style)+'_count.json'));assert counts['drivers_valid']
   dest=dst.parent/('WhiteVNeck' if style else '')
   add(C/kind/(level+'_'+str(style)+'_Crowd_StandingIdle.png'),dest/(level+'.png'))
 for style in ['WhiteWrap','WhiteVNeck']:
  report=check(S/kind/style/'export_validation.json',13);dest=M/'CharacterSuite'/kind
  if style=='WhiteVNeck':dest/=style
  for row in report['files']:add(S/kind/style/row['file'],dest/row['file'])
 add(S/kind/'WhiteWrap/Gameplay_High_Dobok.fbx',M/'Animation/MotionBuilder/_Sources'/('OpenStance_'+kind+'_Mocap_Source.fbx'))
for row in mb['files']:
 src=S/row['file'];style=src.parent.name;kind=src.parent.parent.name;dest=M/'Animation/MotionBuilder'/kind
 if style=='WhiteVNeck':dest/=style
 add(src,dest/src.name);add(src.with_name('validation_'+src.stem+'.json'),dest/('validation_'+src.stem+'.json'))
old={r['file'].replace('\\','/'):r['sha256'] for r in read(M/'FollowupFix/published.json')['files']}
for _,p in mapping:
 rel=p.relative_to(ROOT).as_posix()
 if p.exists() and rel in old:assert sha(p)==old[rel],('Intervening edit',rel)
archive=M/'Archive'/('Before_Crowd_Material_Repair_20261022_'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
def backup(p):
 if p.exists():
  d=archive/p.relative_to(ROOT);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);assert sha(d)==sha(p)
def write(p,s):backup(p);p.write_text(s,encoding='utf-8')
print('Backing up '+str(len(mapping))+' assets',flush=True)
for _,p in mapping:backup(p)
records=[]
for src,dest in mapping:
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);digest=sha(src);assert sha(dest)==digest;records.append({'file':dest.relative_to(ROOT).as_posix(),'sha256':digest})
for kind in KINDS:
 p=M/'CharacterSuite'/kind/'catalog.json';cat=read(p);cat['crowd_face_material_revision']='2026-10-22'
 for level in ['Crowd_Near','Crowd_Far']:
  r=cat['profiles'][level];r['parts']['Head']=6000 if level=='Crowd_Near' else 2400
  counts={str(i):read(C/kind/(level+'_'+str(i)+'_count.json'))['triangles'] for i in [0,1]}
  for field in ['visible_base_triangles','visible_evaluated_total','visible_evaluated_triangles']:r.pop(field,None)
  r['visible_total']=counts['0'];r['visible_totals_by_jacket_style']=counts;r['crowd_face_material_revision']='2026-10-22'
 write(p,json.dumps(cat,indent=2));records.append({'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
for p,link in [(ROOT/'Models and Rigs/START HERE.md','../Resources/Models/ExportMaterialRepair/README.md'),(M/'CharacterSuite/README.md','../ExportMaterialRepair/README.md'),(M/'Animation/README.md','../ExportMaterialRepair/README.md')]:
 write(p,'> Latest repair, 2026-10-22: crowd faces and hair attachment refined; repeated FBX exports now retain eye, mouth and skin material assignments. Runtime FBXs and MotionBuilder targets rebuilt. See [details and limitations]('+link+').\n\n'+p.read_text(encoding='utf-8'))
(S/'published.json').write_text(json.dumps({'archive':str(archive),'files':records,'native_crowd_models':18,'runtime_exports':234,'motionbuilder_targets':36,'catalog_previews':36},indent=2))
(S/'installation_complete.txt').write_text('Verified file copies and hashes. See published.json.\n')
print('Installed '+str(len(mapping))+' assets. Backup: '+str(archive),flush=True)
