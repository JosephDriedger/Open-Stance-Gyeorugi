"""Create a machine-readable entry point after the Blender validation stages."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Resources/Models/CharacterSuite'
catalog={'schema_version':1,'target':'PC_console_fidelity_priority','default_body':'Medium','default_preview':'Medium/Preview.blend','body_types':{},'notes':['Native preview files retain facial FK; gameplay uses the body rig.', 'No automatic marker solve or engine frame-rate validation is claimed.', 'Material parameter drivers require engine-side material setup.']}
for kind in ['Compact','Medium','Stocky','LeanTall','Tall']:
    data=json.loads((OUT/kind/'catalog.json').read_text())
    checks=json.loads((OUT/kind/'validation.json').read_text())
    assert len(checks)==6
    profiles={name:{'blend':f'{kind}/{name}.blend','triangles':p['visible_total'],'bones':p['bones'],'max_influences':p['influence_limit']} for name,p in data['profiles'].items()}
    catalog['body_types'][kind]={'preview':f'{kind}/Preview.blend','catalog':f'{kind}/catalog.json','validation':f'{kind}/validation.json','profiles':profiles}
exports=json.loads((OUT/'export_validation.json').read_text())
assert len(exports)==65 and all(p['passed'] for p in exports.values())
catalog['validation_summary']={'native_files':30,'fbx_roundtrips':65,'crowd_actions_per_body':5,'passed':True}
helmet_checks=OUT/'helmet_validation.json'
rebuilt_checks=OUT/'rebuilt_gear_validation.json'
if rebuilt_checks.exists():
    results=json.loads(rebuilt_checks.read_text());assert len(results['files'])==20
    catalog['helmets']={'source_library':'../HelmetVariants/Helmet_Design_Library.blend','reference_notes':'REBUILT_GEAR.md','validation':'rebuilt_gear_validation.json','styles':['Vented_Crown','Padded_Open_Crown','Perforated_Full_Crown'],'validated_files':20}
    catalog['protectors']={'source_library':'../ProtectorStudy/Chest_Protector_Library.blend','validation':'rebuilt_gear_validation.json','styles':['Quilted_Lace_Back','Smooth_Buckle_Back'],'validated_files':20}
elif helmet_checks.exists():
    results=json.loads(helmet_checks.read_text());assert len(results)==20
    catalog['helmets']={'source_library':'HelmetLibrary.blend','reference_notes':'HELMET_REFERENCES.md','validation':'helmet_validation.json','styles':['Padded_OpenFace','Vented_Foam','Perforated_Foam'],'validated_files':20}
(OUT/'catalog.json').write_text(json.dumps(catalog,indent=2))
print(json.dumps(catalog['validation_summary']))
