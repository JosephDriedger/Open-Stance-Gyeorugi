from pathlib import Path
p=Path(__file__).with_name('visual_review_current.py')
code=p.read_text().replace("ROOT/'Resources/Models/VisualReview_20261016'","ROOT/'Resources/Models/VisualFitRepair/VisualQA'").replace("ROOT/'Resources/Models/CharacterSuite'/kind","ROOT/'Resources/Models/VisualFitRepair'/kind")
code=code.replace('import bpy,sys,json,traceback','import bpy,sys,json,traceback,time')
code=code.replace(' bpy.ops.wm.open_mainfile(filepath=str(source));'," deadline=time.monotonic()+7200\n while not (source.parent/'Gameplay_High_validation.json').exists():\n  if time.monotonic()>deadline:raise RuntimeError('Native build timeout')\n  time.sleep(5)\n bpy.ops.wm.open_mainfile(filepath=str(source));")
exec(compile(code,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
