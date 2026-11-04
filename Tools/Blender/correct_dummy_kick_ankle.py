"""Correct the staged dummy take's world-locked foot orientation, preserving the original."""
import bpy,json,math
from pathlib import Path
from mathutils import Quaternion
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/CorrectedDummyAnkle';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardAnimationReview/Animation_Test.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];original=r.animation_data.action;corrected=original.copy();corrected.name='Dummy_Front_Kick_Local_Ankle';r.animation_data.action=corrected
if corrected.slots:r.animation_data.action_slot=corrected.slots[0]
samples=[];limit=math.radians(35)
for frame in range(1,145):
 s.frame_set(frame);p=r.pose.bones['foot_l'];q=p.rotation_quaternion.copy();q.normalize()
 if q.w<0:q.negate()
 before=q.angle
 if before>limit:q=Quaternion().slerp(q,limit/before)
 samples.append({'frame':frame,'original_local_angle_degrees':math.degrees(before),'corrected_local_angle_degrees':math.degrees(q.angle)})
 p.rotation_quaternion=q;p.keyframe_insert('rotation_quaternion',frame=frame,group='foot_l')
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Animation_Test.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'original_action':original.name,'new_action':corrected.name,'scope':'Conservative 35-degree local rotation bound for this dummy animation, not a mocap retargeting rule or anatomical validation','samples':samples},indent=2))
