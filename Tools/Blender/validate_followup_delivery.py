import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
repair.OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/FollowupFix')
p=Path(__file__).with_name('validate_tailored_delivery.py')
code=p.read_text()
for name in ['body_unchanged','rest_hierarchy_unchanged','animation_keyframes_unchanged']:code=code.replace("report['"+name+"']","report['rig_body_actions_preserved']")
code=code.replace("assert len(r.data.bones)==(25 if crowd else 341)","assert len(r.data.bones)==(25 if crowd else 341)\n   for part in ['Pants']+repair.PANELS:\n    keys=bpy.data.objects[part].data.shape_keys\n    assert keys and all('HipFlex_Clearance_'+side in keys.key_blocks for side in 'lr'),(kind,level,part)")
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
