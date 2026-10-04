"""Validate helmet-fit shape keys and render all hair/helmet combinations."""
import bpy,json,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
from build_character_variations import STYLES,PRESETS
OUT=Path(__file__).resolve().parents[2]/'Resources/Models/CharacterVariations'
try:
 report={}
 for preset in PRESETS:
  name=preset[0];bpy.ops.wm.open_mainfile(filepath=str(OUT/name/'Character.blend'));rig=bpy.data.objects['RIG_Body_Medium'];scene=bpy.context.scene
  checks=[]
  for helmet in range(3):
   for style in range(6):
    rig['HelmetDesign']=helmet;rig['HairStyle']=style;rig['Wear_Helmet']=True;rig['Wear_Hair']=True;rig.update_tag();scene.frame_set(2);scene.frame_set(1);bpy.context.view_layer.update()
    objects=list(bpy.data.collections['Hairstyle_'+STYLES[style]].objects)
    if helmet==0:
     for o in objects:assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<1e-5 for v in o.data.vertices)
    assert all(not o.hide_render and abs(o.data.shape_keys.key_blocks['HelmetFit'].value-1)<1e-6 for o in objects)
    assert all(d.driver.is_valid for o in objects for d in o.data.shape_keys.animation_data.drivers)
    helmet_name=['Vented_Crown','Padded_Open_Crown','Perforated_Full_Crown'][helmet]
    assert all(not o.hide_render for o in bpy.data.collections['Helmet_'+helmet_name].objects)
    if name=='Female_Athletic':
     scene.render.resolution_x=800;scene.render.resolution_y=900;scene.render.resolution_percentage=100
     view.camera(scene,(.65,-1,1.80),(0,0,1.64),.43);scene.render.filepath=str(OUT/f'Helmet_{helmet}_{STYLES[style]}_Front.png');bpy.ops.render.render(write_still=True)
     if style in [3,4,5]:
      view.camera(scene,(.65,1,1.75),(0,.025,1.61),.45);scene.render.filepath=str(OUT/f'Helmet_{helmet}_{STYLES[style]}_Rear.png');bpy.ops.render.render(write_still=True)
    rig['Wear_Helmet']=False;rig.update_tag();scene.frame_set(2);scene.frame_set(1);bpy.context.view_layer.update()
    assert all(abs(o.data.shape_keys.key_blocks['HelmetFit'].value)<1e-6 for o in objects)
    checks.append({'helmet':helmet_name,'hair':STYLES[style],'compression_and_restore_passed':True})
  report[name]={'checks':checks,'passed':True,'limitations':'Static fitted rest-pose previews; no secondary hair simulation or exhaustive combat collision test.'}
  native_path=OUT/name/'validation.json';native=json.loads(native_path.read_text())
  for style in STYLES:native['styles'][style]['parts']=len(bpy.data.collections['Hairstyle_'+style].objects)
  native_path.write_text(json.dumps(native,indent=2))
  (OUT/'helmet_fit_validation.json').write_text(json.dumps(report,indent=2))
 (OUT/'helmet_fit.log').write_text('COMPLETE')
except:(OUT/'helmet_fit.log').write_text(traceback.format_exc());raise
