"""Archive a completed 36-target import audit, with source hashes and explicit limits."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = json.loads((root / 'Saved/Logs/belt_chain_targets.json').read_text())
log = (root / 'Saved/Logs/belt_chain_targets.txt').read_text()
engine_log = (root / 'Saved/Logs/belt_target_audit_fixed_20261028.log').read_text(errors='replace')
kinds = ('Medium', 'Compact', 'Stocky', 'LeanTall', 'Tall', 'Male_Athletic',
         'Male_Lean', 'Female_Athletic', 'Female_Strong')
expected = {f'{k}{s}_{o}' for k in kinds for s in ('', '_VNeck') for o in ('Dobok', 'Sparring')}
assert 'DONE 36 targets' in log and len(rows) == 36
assert {r['tag'] for r in rows} == expected
assert all('error' not in r and r['bones'] == 358 and r['chain_bones'] == 16
           and r['chain_parents_ok'] for r in rows)
for row in rows:
    with open(row['fbx'], 'rb') as stream:
        row['source_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
report = {
    'import_and_chain_structure_passed': True,
    'targets': len(rows),
    'existing_project_body_comparisons': sum('project_body_bones' in r for r in rows),
    'missing_project_body_comparisons': [r['tag'] for r in rows if 'comparison_unavailable' in r],
    'direct_shared_skeleton_compatible': False,
    'import_warning_counts': {
        'invalid_bind_pose': engine_log.count('Not valid bind pose'),
        'zero_length_normal': engine_log.count('Compute a zero length normal vector'),
    },
    'limitations': [
        'Root wrappers differ from the existing project body root; do not directly reuse that skeleton.',
        'Bind-pose warnings occur during FBX import. Successful skeleton import is not a skinning or bind-pose visual pass.',
        'Zero-length-normal tangent warnings require a separate mesh/shading inspection; this audit does not repair them.',
        'Rest-position comparison does not compare rotation, scale, materials or animation deformation.',
        'No recorded mocap take, simulated cloth acceptance or full wardrobe integration is covered.',
    ],
    'rows': rows,
}
dest = root / 'Resources/Models/FinalRefinement/BeltTargetImportAudit'
dest.mkdir(exist_ok=True)
(dest / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
