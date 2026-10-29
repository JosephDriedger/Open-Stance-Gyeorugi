import sys,runpy,traceback,json,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_collar_ears as fix
try:
    deadline=time.monotonic()+3600
    while not (fix.OUT/'Medium/Sample_Kick_validation.json').exists():
        assert time.monotonic()<deadline
        time.sleep(5)
    p=Path(__file__).with_name('check_visual_fit_physics.py')
    code=p.read_text().replace('import repair_visual_fit as fix','import repair_collar_ears as fix')
    exec(compile(code,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
    p=Path(__file__).with_name('finalize_visual_fit_demo.py')
    code=p.read_text().replace('VisualFitRepair','CollarEarRepair')
    exec(compile(code,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
    import bpy,extend_garment_repairs as base
    source=fix.ROOT/'Resources/Models/ProtectorReferenceV2/Chest_Protector_Library.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
    r=bpy.data.objects['RIG_Body_Medium'];signature=base.signature(r);actions=base.actions()
    changes=fix.repair(s);assert signature==base.signature(r) and actions==base.actions()
    out=fix.OUT/'Gear';out.mkdir(exist_ok=True);dest=out/source.name
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
    (out/'validation.json').write_text(json.dumps({'passed':True,'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'repair':changes},indent=2))
except:(fix.OUT/'finish_error.log').write_text(traceback.format_exc());raise
