"""Determine whether the last-frame belt shape is moving or actually trapped."""
import bpy,sys,json,math,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
import extend_garment_repairs as base
root=a.ROOT/'Resources/Models/FinalRefinement';out=root/'BalancedExtended/Medium';out.mkdir(parents=True,exist_ok=True)
assert not (out/'validation.json').exists()
bpy.ops.wm.open_mainfile(filepath=str(root/'BalancedBeltPresets/Medium/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];signature,actions=base.signature(r),base.actions()
s.frame_set(1);s.frame_end=288;s.cycles.samples=8
for o in s.objects:
    for m in o.modifiers:
        if m.type=='CLOTH':m.point_cache.frame_end=288
proxy=bpy.data.objects['SIM_Shared_Belt_Tails'];previous=None;rows=[];started=time.monotonic()
for frame in range(1,289):
    s.frame_set(frame);ev=proxy.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pts=[v.co.copy() for v in me.vertices]
    assert all(math.isfinite(x) and abs(x)<5 for p in pts for x in p)
    speed=max((p-q).length for p,q in zip(pts,previous))*s.render.fps/s.render.fps_base if previous else 0
    previous=pts;ev.to_mesh_clear()
    if frame%24==0:print('SETTLE',frame,round(time.monotonic()-started,1),flush=True)
    if frame in [144,216,288]:
        rows.append({'frame':frame,'maximum_speed_m_per_s':speed,'z_span_m':max(p.z for p in pts)-min(p.z for p in pts)})
        a.render(s,r,1,out,'Front_'+str(frame),(.2,-4,1.3),(0,0,.96),1.25,480,540)
assert base.signature(r)==signature and base.actions()==actions
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'Candidate.blend'),compress=True)
(out/'validation.json').write_text(json.dumps({'frames':288,'rig_actions_preserved':True,'rows':rows,'production_installed':False},indent=2))
