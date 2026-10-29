from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'Resources/Models';S=M/'GarmentRollout';report=json.loads((S/'published.json').read_text());archive=Path(report['archive'])
def edit(p,content):
 dest=archive/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(p,dest)
 p.write_text(content,encoding='utf-8')
p=M/'Animation/Samples/README.md';s=p.read_text(encoding='utf-8');s=s.replace('The characterized MotionBuilder targets still contain earlier garments.','The characterized MotionBuilder targets and other LODs now include the garment repairs; see ../../GarmentRollout/README.md.');edit(p,s)
for p in [M/'CharacterSuite/REBUILD_REPORT.md',M/'CharacterVariations/README.md']:
 s=p.read_text(encoding='utf-8');notice='> Garment update 2026-10-13: the current primary-uniform repairs are published across preview, gameplay, crowd, animation and MotionBuilder files. See [current scope and validation](../GarmentRollout/README.md). The build details below describe the preceding general character rebuild.\n\n'
 if not s.startswith(notice):edit(p,notice+s)
p=M/'ROMRepair/README.md';s=p.read_text(encoding='utf-8').replace('## Scope still pending','## Scope of the preceding pass').replace('Preview, Gameplay_Mid/Far, Crowd_Near/Far, alternate jackets, animation master scenes and characterized MotionBuilder targets retain their earlier garments. Their skeletons remain usable, but they should not be used as visual evidence of this repair.','This preceding pass did not update Preview, Gameplay_Mid/Far, Crowd_Near/Far, animation masters or MotionBuilder targets. Those files are now updated by GarmentRollout. Alternate jacket styles remain outside the primary-uniform repair.');edit(p,s)
print('Updated current guides and preserved prior versions in the archive')
