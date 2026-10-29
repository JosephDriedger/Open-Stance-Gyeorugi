"""Headless regression for changing, clearing and rejecting a self-referencing belt leader.

Run through UnrealEditor-Cmd -run=pythonscript -script=<this file>. No assets are saved.
"""
import json
import traceback
from pathlib import Path
import unreal

out = Path('D:/Open-Stance-Gyeorugi/Saved/Logs/belt_leader_lifecycle.json')
report = {'passed': False, 'checks': []}
try:
    follower = unreal.new_object(unreal.SkeletalMeshComponent)
    first = unreal.new_object(unreal.SkeletalMeshComponent)
    second = unreal.new_object(unreal.SkeletalMeshComponent)
    instance = unreal.new_object(unreal.OpenStanceBeltFollowerAnimInstance, outer=follower)
    for label, source, expected in (
        ('initial leader', first, first),
        ('same leader again', first, first),
        ('replace leader', second, second),
        ('clear leader', None, None),
        ('reject self leader', follower, None),
        ('restore after rejection', first, first),
    ):
        instance.set_leader(source)
        assert instance.get_leader() == expected, label
        report['checks'].append(label)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('BELT_LEADER_LIFECYCLE ' + json.dumps(report))
