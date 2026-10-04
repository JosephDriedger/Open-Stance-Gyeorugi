"""Promote validated staging files, preserving prior suite artifacts in an archive."""
import json,shutil,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];MODELS=ROOT/'Resources/Models';STAGE=MODELS/'GearUpgrade';SUITE=MODELS/'CharacterSuite'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall'];PROFILES=['Preview','Gameplay_High','Gameplay_Mid','Gameplay_Far']
exports=json.loads((STAGE/'export_validation.json').read_text());assert len(exports)==15 and all(v['passed'] for v in exports.values())
checks={}
for kind in KINDS:
 for profile in PROFILES:
  check=json.loads((STAGE/kind/(profile+'_gear_validation.json')).read_text());assert check['passed'];checks[kind+'/'+profile]=check
pose=json.loads((STAGE/'pose_validation.json').read_text());assert len(pose)==20 and all(v['passed'] for v in pose.values())
archive=MODELS/'Archive'/('Before_Rebuilt_Gear_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));archive.mkdir(parents=True,exist_ok=False)
def backup(path):
 if path.exists():
  dest=archive/path.relative_to(SUITE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
for name in ['catalog.json','README.md','export_validation.json','HELMET_REFERENCES.md']:
 backup(SUITE/name)
for kind in KINDS:
 for name in ['catalog.json','validation.json']:backup(SUITE/kind/name)
 for profile in PROFILES:
  name=profile+'.blend';backup(SUITE/kind/name);shutil.copy2(STAGE/kind/name,SUITE/kind/name)
  if profile!='Preview':
   name=profile+'_Sparring.fbx';backup(SUITE/kind/name);shutil.copy2(STAGE/kind/name,SUITE/kind/name)
 shutil.copy2(STAGE/kind/'Rebuilt_Gear.png',SUITE/kind/'Rebuilt_Gear.png')
 catpath=SUITE/kind/'catalog.json';cat=json.loads(catpath.read_text())
 for category,styles in [('Helmet',['Vented_Crown','Padded_Open_Crown','Perforated_Full_Crown']),('Protector',['Quilted_Lace_Back','Smooth_Buckle_Back'])]:
  cat['variants'][category]=[{'style':s,'selector':i,'collection':'Rebuilt_'+category+'_'+s,'object_prefix':category+'_'+s+'__'} for i,s in enumerate(styles)]
 for profile in PROFILES[1:]:
  data=checks[kind+'/'+profile];cat['profiles'][profile]['visible_evaluated_triangles']=data['visible_evaluated_triangles'];cat['profiles'][profile]['visible_total']=data['visible_total']
  cat['profiles'][profile].pop('base_triangles',None)
 cat['rebuilt_gear']={'validation':'../rebuilt_gear_validation.json','selectors':['HelmetStyle','ProtectorStyle'],'export_default':'Vented_Crown + Quilted_Lace_Back','preview':'Rebuilt_Gear.png'}
 catpath.write_text(json.dumps(cat,indent=2))
 validation_path=SUITE/kind/'validation.json';native=json.loads(validation_path.read_text())
 for profile in PROFILES:
  native[profile].pop('weighted_meshes',None)
  native[profile]['rebuilt_gear_parts']=checks[kind+'/'+profile]['gear_parts']
  native[profile]['rebuilt_gear_validation']='../rebuilt_gear_validation.json'
  native[profile]['gear_pose_checks_passed']=True
 validation_path.write_text(json.dumps(native,indent=2))
old=json.loads((SUITE/'export_validation.json').read_text());old.update(exports);(SUITE/'export_validation.json').write_text(json.dumps(old,indent=2))
(SUITE/'rebuilt_gear_validation.json').write_text(json.dumps({'files':checks,'pose_tests':pose,'exports':exports,'archive':str(archive)},indent=2))
root=json.loads((SUITE/'catalog.json').read_text())
root['helmets']={'styles':['Vented_Crown','Padded_Open_Crown','Perforated_Full_Crown'],'source_library':'../HelmetVariants/Helmet_Design_Library.blend','validated_files':20,'validation':'rebuilt_gear_validation.json'}
root['protectors']={'styles':['Quilted_Lace_Back','Smooth_Buckle_Back'],'source_library':'../ProtectorStudy/Chest_Protector_Library.blend','validated_files':20,'validation':'rebuilt_gear_validation.json'}
for kind in KINDS:
 for profile in PROFILES[1:]:root['body_types'][kind]['profiles'][profile]['triangles']=checks[kind+'/'+profile]['visible_total']
(SUITE/'catalog.json').write_text(json.dumps(root,indent=2))
readme=SUITE/'README.md';text=readme.read_text()
text=text.replace('Helmet options have been rebuilt from three real manufacturer references. `HelmetStyle` is now 0 = Padded Open Face, 1 = Vented Foam, 2 = Perforated Foam. See [helmet references and construction notes](HELMET_REFERENCES.md) for the Century, adidas and Daedo source pages and the actual features modeled.', 'The approved rebuilt gear is fitted to all five bodies in preview and gameplay files. `HelmetStyle`: 0 = Vented Crown, 1 = Padded Open Crown, 2 = Perforated Full Crown. `ProtectorStyle`: 0 = Quilted Lace Back, 1 = Smooth Buckle Back. Each choice has separate editable parts in a `Rebuilt_*` collection. `Wear_Helmet` and `Wear_Protector` toggle the complete assemblies. See [rebuilt gear notes](REBUILT_GEAR.md).')
text=text.replace('Protective equipment has standard and padded variants.', 'Gloves and foot protection retain standard and padded variants; helmets and chest protectors use the rebuilt designs described below.')
start=text.find('After the build and finalize stages, run `rebuild_reference_helmets.py`')
end=text.find('\n\n',start)
if start!=-1:text=text[:start]+'The older `rebuild_reference_helmets.py` produces superseded helmets and must not be run as the final gear stage. Rebuild current gear with `integrate_rebuilt_gear.py`, validate using `check_rebuilt_gear_exports.py` and `check_rebuilt_gear_poses.py`, inspect renders, then promote using `publish_rebuilt_gear.py`. The staging directory is `../GearUpgrade`; prior suite files are copied into `../Archive` during promotion.'+text[end:]
readme.write_text(text)
(SUITE/'REBUILT_GEAR.md').write_text('''# Rebuilt gear integration

All five body presets have the approved helmet designs and rebuilt chest protectors in Preview, Gameplay_High, Gameplay_Mid and Gameplay_Far. The default sparring FBX uses Vented Crown plus Quilted Lace Back. Alternate designs remain modular in Blender and can be exported by selecting their properties first.

| Tier | Helmet target triangles | Protector target triangles |
| --- | ---: | ---: |
| Preview | 160,000 | 90,000 |
| Gameplay High | 30,000 | 22,000 |
| Gameplay Mid | 15,000 | 11,000 |
| Gameplay Far | 6,000 | 10,000 |

Budgets apply to the complete selected assembly; tiny separate parts can cause small overruns. Exact totals and fitting scales are in rebuilt_gear_validation.json. The original higher-density study libraries remain unchanged. New parts use the existing head and spine bones, with at most two influences. Color remains driven by MatchSide.

Rebuilt_Gear.png in each body folder shows the fit. Twenty saved native files have passed gear weight, selector and toggle checks. All five gear choices per file passed a posed attachment check. Fifteen updated sparring FBXs were re-imported and checked for the 341-bone body skeleton, normalized weights and selected gear. Existing no-gear and crowd exports were not changed.

These checks establish attachment and export integrity, not collision-free motion in every animation or an engine frame-rate target. Materials still require the documented Unreal material setup/baking. This integration does not implement an in-game character-creation interface.

Source libraries: ../HelmetVariants/Helmet_Design_Library.blend and ../ProtectorStudy/Chest_Protector_Library.blend. Earlier helmet validation reports describe superseded geometry; use rebuilt_gear_validation.json for the current gear.
''')
(STAGE/'published.json').write_text(json.dumps({'archive':str(archive),'native_files':20,'sparring_exports':15,'passed':True},indent=2))
print('Published 20 native files and 15 sparring exports. Backup: '+str(archive))
