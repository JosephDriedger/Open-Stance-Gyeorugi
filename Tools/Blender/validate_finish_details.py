import bpy,sys,json,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
import refine_character_finish as fix
import tailor_doboks as profiles
out=fix.OUT
try:
 rows=[]
 for kind in build.PRESETS:
  for level in profiles.LEVELS:
   report=out/kind/(level+'_validation.json')
   while not report.exists():time.sleep(5)
   record=json.loads(report.read_text());bpy.ops.wm.open_mainfile(filepath=str(out/kind/record['file']))
   s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
   assert s.get('FinishRefinementV2')=='2026-10-18'
   knot=bpy.data.objects['Belt'];assert len(knot.data.vertices)==312 and not any(m.type=='SOLIDIFY' for m in knot.modifiers)
   core=bpy.data.objects.get('Hair_Low_Ponytail__Ponytail_Core');assert core
   for style in [0,4]:
    for helmet in [False,True]:
     r['HairStyle']=style;r['Wear_Hair']=True;r['Wear_Helmet']=helmet;build.refresh(r)
     assert core.hide_render==(style!=4)
     assert core.data.shape_keys.key_blocks['HelmetFit'].value==int(helmet)
   caps=[o for o in s.objects if o.type=='MESH' and 'Scalp_Coverage' in o.name and 'Crew_Cut' not in o.name]
   for o in caps:
    assert o.data.uv_layers.get('NaturalHairlineUV'),o.name
    bs=next(n for n in o.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    assert bs.inputs['Alpha'].is_linked and bs.inputs['Alpha'].links[0].from_node.image.packed_file
   rows.append({'preset':kind,'profile':level,'hair_caps':len(caps),'knot_vertices':312,'ponytail_visibility_and_helmet_fit':True})
 (out/'finish_checks.json').write_text(json.dumps({'passed':True,'files':rows},indent=2))
except:(out/'finish_checks_error.log').write_text(traceback.format_exc());raise
