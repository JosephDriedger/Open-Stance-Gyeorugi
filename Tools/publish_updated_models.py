"""Publish only fully validated updated assets, archiving replaced files first."""
from pathlib import Path
import json,hashlib,shutil,datetime,sys
ROOT=Path(__file__).resolve().parents[1];MODELS=ROOT/'Resources/Models';STAGE=MODELS/'UpdatedBuild'
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
PROFILES=['Preview','Gameplay_High','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far']
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def checked(p,count,key):
 r=read(p);assert r['passed'] and len(r[key])==count,p
 return r
def publish():
 mapping=[];summary={}
 def add(source,dest):assert source.is_file(),source;mapping.append((source,dest))
 for kind in KINDS:
  d=STAGE/kind
  checked(d/'native_validation.json',7,'files');checked(d/'controls_validation.json',7,'files');checked(d/'hair_alignment_validation.json',30,'checks')
  exports=checked(d/'export_validation.json',14,'files')
  for row in exports['files']:assert row['sha256']==digest(d/row['file']),('Export changed after validation',kind,row['file'])
  suite=MODELS/'CharacterSuite'/kind
  for profile in PROFILES:add(d/(profile+'.blend'),suite/(profile+'.blend'))
  for row in exports['files']:
   source=d/row['file']
   target=MODELS/'Animation/MotionBuilder/_Sources'/row['file'] if 'Mocap_Source' in row['file'] else suite/row['file']
   add(source,target)
  add(d/f'OpenStance_{kind}_Animation.blend',MODELS/'Animation'/f'OpenStance_{kind}_Animation.blend')
  for p in d.glob('*.json'):
   if p.name not in ['export_smoke.json']:add(p,suite/p.name)
  for name in ['Preview','Portrait','Updated_Sparring','Gameplay_High','Gameplay_Mid','Gameplay_Far','Crowd_Near','Crowd_Far','Crowd_StandingIdle','Crowd_SeatedIdle','Crowd_SeatedClap','Crowd_Cheer','Crowd_Wave','FBX_Reimport_Sparring']:
   add(d/(name+'.png'),suite/(name+'.png'))
  add(d/'Updated_Sparring.png',suite/'Rebuilt_Gear.png')
  if kind.startswith(('Male_','Female_')):
   add(d/'Preview.blend',MODELS/'CharacterVariations'/kind/'Character.blend')
   add(d/'Portrait.png',MODELS/'CharacterVariations'/kind/'Portrait.png')
   add(d/'Preview.png',MODELS/'CharacterVariations'/kind/'Full_Body.png')
  for suffix,source in [('',d/f'OpenStance_{kind}_Mocap_Source.fbx'),('_Sparring',d/'Gameplay_High_Sparring.fbx')]:
   name='OpenStance_'+kind+suffix;mb=STAGE/'MotionBuilder'/kind;report=read(mb/f'validation_{name}.json')
   assert report['characterized'] and report['control_rig'] and report['reopened_successfully']
   assert report['source_sha256']==digest(source),('Stale MotionBuilder target',name)
   add(mb/(name+'.fbx'),MODELS/'Animation/MotionBuilder'/kind/(name+'.fbx'))
   add(mb/f'validation_{name}.json',MODELS/'Animation/MotionBuilder'/kind/f'validation_{name}.json')
  summary[kind]={p:read(d/(p+'_validation.json')) for p in PROFILES if p!='Preview'}
 checked(STAGE/'workspace_validation.json',9,'scenes')
 add(STAGE/'OpenStance_Characters_Workspace.blend',MODELS/'OpenStance_Characters_Workspace.blend')
 add(STAGE/'workspace_validation.json',MODELS/'Animation/workspace_validation.json')
 for p in (STAGE/'Textures').glob('*.png'):add(p,MODELS/'CharacterSuite/Textures'/p.name)
 if '--publish' not in sys.argv:
  print(json.dumps({'ready':True,'files':len(mapping),'presets':len(KINDS)},indent=2));return
 archive=MODELS/'Archive'/('Before_Updated_Specs_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));archive.mkdir(parents=True)
 records=[]
 def backup(dest):
  if dest.exists():
   saved=archive/dest.relative_to(ROOT);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
   assert digest(saved)==digest(dest)
 def write(dest,text):
  backup(dest);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text,encoding='utf-8')
 for source,dest in mapping:
  backup(dest);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);sha=digest(source);assert digest(dest)==sha
  records.append({'file':str(dest.relative_to(ROOT)),'sha256':sha})
 # Preserve the combined workspace's immediately prior version in the same archive.
 animation_guide='''# Updated animation and mocap library

All nine presets now use the updated visual specifications: Medium, Compact, Stocky, LeanTall, Tall, Male_Athletic, Male_Lean, Female_Athletic and Female_Strong. The white uniform overlaps the trousers; the latest chest guard extends over the upper belt knot. Hair and eyebrow choices match the current creator previews.

## Start a mocap test

Open `MotionBuilder/Medium/OpenStance_Medium.fbx` inside MotionBuilder for the dobok target, or `OpenStance_Medium_Sparring.fbx` for the gear version. These are separate characterized FK/IK targets with the same underlying body skeleton. The other preset folders have the same pair. Do not rely on the Windows default FBX viewer for rig or material testing.

Use `OpenStance_Medium_Animation.blend` for Blender cleanup, or choose the matching preset's animation file. The combined `../OpenStance_Characters_Workspace.blend` contains nine Fighter scenes; individual files load more quickly. Select `RIG_Body_<preset>` for body animation and customization; unhide `RIG_Face_<preset>` for facial bone animation.

Confirm the proposed 41-marker layout in `Docs/Mocap_Marker_Set.md` with the capture lab. Collect a calibrated pose and labeled movement C3D, performer measurements, capture rate, units and axes, plus a solved FBX if available. Calibrate the MotionBuilder Actor to the actual session, solve/retarget, plot/bake to the fighter skeleton, and export solved motion. Import into a separate Blender collection and transfer/retarget to the matching body rig. Verify rest transforms and local axes, not just bone names.

## Animation structure

The body rig retains 341 bones and the native Blender face retains 874 bones. Body FK, hands, toes and corrective/helper collections are retained, along with separate NLA tracks for mocap, hand-keyed cleanup and finger overrides. Keep DIAG actions muted: they are synthetic deformation checks, not captured moves. Match the capture FPS and frame range before importing animation. Marker guides are approximate visual references, not calibrated data.

The capture layout does not record finger articulation, toe curl or facial expressions. Add those separately. The facial rig supports bone animation; Blender DNA/RigLogic and expression-slider controls are not implemented. Long hair follows the head rigidly; secondary hair simulation and exhaustive combat collision testing remain unfinished.

## Current controls and exports

HairStyle: 0 Crew Cut, 1 Side Part, 2 Curly Crop, 3 Chin Length Bob, 4 Low Ponytail, 5 Compact Bun. EyebrowStyle: 0 Natural, 1 Straight, 2 Full, 3 Soft Arch, 4 High Arch, 5 Thin Groomed. Wear_Hair and Wear_Eyebrows are independent. HairColor also controls eyebrow color.

HelmetDesign: 0 Vented Crown, 1 Padded Open Crown, 2 Perforated Full Crown. ProtectorDesign: 0 Quilted Lace Back, 1 Smooth Buckle Back. Wear_Helmet automatically drives hair HelmetFit. MatchSide: 0 blue, 1 red. HeadStyle, JacketStyle, GlovesStyle, FootGuardsStyle, SkinTone and EyeColor expose the existing modular choices. Style options live in native Blender; FBX files are snapshots of the selected default style/outfit, not a game-engine customization UI.

Body-animation FBXs use the 341-bone body skeleton and a body-bound head. Full facial deformation stays in the native files. Crowd files use a separate 25-bone rig and require retargeting for fighter motion. Export only the intended meshes and body skeleton; exclude studio objects, marker guides and the separate face armature.

## What was verified

Native files were reopened and checked for selectors, helmet fitting, driver references, marker counts and body deformation. Runtime FBXs were reimported to check skeleton count, weights, embedded skin textures and crowd actions. Hair alignment was compared against the full-detail source. MotionBuilder targets passed characterization, control-rig creation, save/reopen and wrist movement checks. No actual marker take has yet validated the complete capture solve.

See `../CharacterSuite/REBUILD_REPORT.md` for published assets and recovery information. Older CreatorFighters/TestFighter/GearUpgrade folders are retained pipeline history; use this library and the root Models and Rigs shortcuts for current work.
'''
 write(MODELS/'Animation/README.md',animation_guide)
 write(MODELS/'CharacterSuite/README.md','''# Updated character suite

Nine presets share the updated models and modular controls. Each folder contains Preview (full body and face rigs), Gameplay_High/Mid/Far (341-bone body rig), and Crowd_Near/Far (25-bone crowd rig). Gameplay FBXs include Dobok and Sparring snapshots. Crowd FBXs include five baked clips: StandingIdle, SeatedIdle, SeatedClap, Cheer and Wave.

Use the native files to select hair, eyebrows, heads, uniforms and equipment. Only selected parts are included in each default FBX export. Embedded albedo textures are baked for portability; native procedural material detail can differ between applications. These authored body/face variants share the original base and skin maps, rather than being separate scans.

The current helmet selector is HelmetDesign and the current chest guard selector is ProtectorDesign. See ../Animation/README.md for controls, mocap workflow and limitations. Per-preset validation JSON and catalog.json record actual evaluated polygon totals and checks. REBUILD_REPORT.md identifies the current published build and the archive of replaced files.
''')
 write(MODELS/'CharacterVariations/README.md','''# Current male/female character presets

Male_Athletic, Male_Lean, Female_Athletic and Female_Strong now match the updated animation, gameplay and crowd suite. Open Character.blend and select RIG_Body_<preset> for customization. These are authored variations of the same original base character, with 341 body bones and a separate 874-bone face rig.

All four include six hairstyles, six eyebrow styles, three helmet designs, two chest protectors and the existing head, uniform, glove, foot-pad and color controls. Eyebrows follow the facial rig in full-detail native files. Wear_Helmet drives fitted hair shape keys; long hair remains rigidly head-bound without secondary simulation. The latest chest guards overlap the top of the belt knot.

The corresponding characterized mocap targets are now in ../Animation/MotionBuilder/<preset> and gameplay/crowd exports are in ../CharacterSuite/<preset>. See ../Animation/README.md for the current control list and capture workflow. Older standalone hairstyle/helmet gallery images may precede the latest consolidated rebuild; per-preset Portrait/Full_Body and CharacterSuite images are current.
''')
 for kind,profiles in summary.items():
  write(MODELS/'CharacterSuite'/kind/'catalog.json',json.dumps({'revision':'Updated specifications 2026-10-05','preset':kind,'profiles':profiles},indent=2))
 report={'revision':'Updated specifications 2026-10-05','presets':KINDS,'native_files':63,'runtime_exports':126,'characterized_targets':18,'archive':str(archive),'files':records,'real_capture_tested':False}
 write(MODELS/'CharacterSuite/catalog.json',json.dumps(report,indent=2))
 write(MODELS/'CharacterSuite/REBUILD_REPORT.md',f'''# Updated model rebuild

Published nine presets, 63 individual native files, 126 runtime/source FBXs, 18 characterized MotionBuilder targets and the combined nine-scene workspace. Current gear, hair and eyebrows are included in the animation and gameplay families. The original files were preserved in `{archive.relative_to(ROOT).as_posix()}` before replacement.

The full hash manifest is catalog.json. Native rig/selector checks, customization-driver checks, reduced-hair alignment, FBX reimport checks and MotionBuilder save/reopen tests passed. This does not certify a real capture solve or every possible combat collision. No Unreal Content packages were reimported by this asset rebuild.

Open the Models and Rigs folder at the repository root for categorized entry points. Start body capture tests with Animation/MotionBuilder/Medium/OpenStance_Medium.fbx (dobok) or OpenStance_Medium_Sparring.fbx (gear).
''')
 (archive/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 (STAGE/'published.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({'published':True,'files':len(records),'archive':str(archive)},indent=2))
if __name__=='__main__':publish()
