import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import tailor_doboks as repair
repair.OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/ExportMaterialRepair');repair.OUT.mkdir(exist_ok=True)
p=Path(__file__).with_name('export_tailored_doboks.py');code=p.read_text()
code=code.replace("native=OUT/kind;d=", "native=OUT/kind;native.mkdir(exist_ok=True);d=")
code=code.replace("while not all((native/(p+'_validation.json')).exists() for p in repair.LEVELS):","while False:")
code=code.replace("str(native/(level+'.blend'))","str(build.ROOT/'Resources/Models'/('CrowdFaceRefinement' if level.startswith('Crowd') else 'CharacterSuite')/kind/(level+'.blend'))")
code=code.replace("meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert meshes","meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert meshes\n  head=next(o for o in meshes if o.name.split('.')[0]=='Head')\n  assert len({p.material_index for p in head.data.polygons})>=3,(name,'lost head material assignments')")
exec(compile(code,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
